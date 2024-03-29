import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from .const import (
    DOMAIN,
    FMISID_LOCATIONS,
    CONF_LOCATION,
    CONF_HOURS,
    CONF_FORECAST_HOURS,
    CONF_STEP, FMISID_VALUES, CONF_OVERLAP
)
from .session import FMIWaterLevelException, FMIWaterLevelSession

_LOGGER = logging.getLogger(__name__)

CONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LOCATION): vol.All(cv.string, vol.In(FMISID_LOCATIONS)),
        vol.Required(CONF_HOURS, default=36): cv.positive_int,
        vol.Required(CONF_FORECAST_HOURS, default=36): cv.positive_int,
        vol.Required(CONF_STEP, default=30): cv.positive_int,
        vol.Required(CONF_OVERLAP, default=300): cv.positive_int,
    }
)

RECONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LOCATION): vol.All(cv.string, vol.In(FMISID_LOCATIONS)),
        vol.Required(CONF_HOURS): cv.positive_int,
        vol.Required(CONF_FORECAST_HOURS): cv.positive_int,
        vol.Required(CONF_STEP): cv.positive_int,
        vol.Required(CONF_OVERLAP): cv.positive_int,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, any]) -> str:
    try:
        fmisid = FMISID_VALUES[FMISID_LOCATIONS.index(data[CONF_LOCATION])]
        session = FMIWaterLevelSession(fmisid, data[CONF_HOURS], data[CONF_FORECAST_HOURS], data[CONF_STEP], data[CONF_OVERLAP])
        await hass.async_add_executor_job(session.call_api, True)
        await hass.async_add_executor_job(session.call_api, False)

    except FMIWaterLevelException:
        raise ConnectionProblem

    return data[CONF_LOCATION]


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, any] = None) -> FlowResult:

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=CONFIGURE_SCHEMA)

        await self.async_set_unique_id(f"fmi_waterlevel_{FMISID_VALUES[FMISID_LOCATIONS.index(user_input[CONF_LOCATION])]}_{user_input[CONF_HOURS]}_{user_input[CONF_FORECAST_HOURS]}")
        self._abort_if_unique_id_configured()

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except ConnectionProblem:
            errors["base"] = "connection_problem"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info, data=user_input)

        return self.async_show_form(step_id="user", data_schema=CONFIGURE_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, any] = None) -> FlowResult:
        if user_input is None:
            return self.async_show_form(step_id="init", data_schema=vol.Schema(
                {
                    vol.Required(CONF_OVERLAP, default=self._config_entry.data.get(CONF_OVERLAP)): cv.positive_int,
                    vol.Required(CONF_STEP, default=self._config_entry.data.get(CONF_STEP)): cv.positive_int,
                })
            )

        errors = {}

        try:
            user_input[CONF_LOCATION] = self._config_entry.data[CONF_LOCATION]
            user_input[CONF_HOURS] = self._config_entry.data[CONF_HOURS]
            user_input[CONF_FORECAST_HOURS] = self._config_entry.data[CONF_FORECAST_HOURS]
            await validate_input(self.hass, user_input)
        except ConnectionProblem:
            errors["base"] = "connection_problem"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            self.hass.config_entries.async_update_entry(self._config_entry, data=user_input, options=self._config_entry.options)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(step_id="init", data_schema=RECONFIGURE_SCHEMA, errors=errors)


class ConnectionProblem(HomeAssistantError):
    """Error to indicate there is an issue with the connection"""
