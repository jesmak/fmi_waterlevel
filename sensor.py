import logging
from datetime import (timedelta, datetime)
from typing import Any, Callable, Dict, Optional

from aiohttp import ClientError

from homeassistant import config_entries, core
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)

from .session import FMIWaterLevelSession
from .const import CONF_HOURS, CONF_FORECAST_HOURS, CONF_LOCATION, CONF_STEP, CONF_OVERLAP, DOMAIN, FMISID_LOCATIONS, FMISID_VALUES

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=10)
ATTRIBUTION = "Data provided by Finnish Meteorological Institute (FMI)"

ATTR_OBSERVATIONS = "observations"
ATTR_FORECAST = "forecast"
ATTR_LATEST_DATE = "latest_date"
ATTR_LATEST_WATERLEVEL = "latest_waterlevel"
ATTR_LOCATION = "location"
ATTR_DATE = "date"
ATTR_WATERLEVEL = "waterlevel"


async def async_setup_platform(
        hass: HomeAssistantType,
        config: ConfigType,
        async_add_entities: Callable,
        discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    if config[CONF_LOCATION] in FMISID_LOCATIONS:
        fmisid = FMISID_VALUES[FMISID_LOCATIONS.index(config[CONF_LOCATION])]
        session = FMIWaterLevelSession(fmisid, config[CONF_HOURS], config[CONF_FORECAST_HOURS], config[CONF_STEP], config[CONF_OVERLAP])
        await hass.async_add_executor_job(session.call_api, True)
        await hass.async_add_executor_job(session.call_api, False)
        async_add_entities(
            [FMIWaterLevelSensor(session, fmisid, config[CONF_HOURS], config[CONF_FORECAST_HOURS])],
            update_before_add=True
        )


async def async_setup_entry(hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry, async_add_entities):
    config = hass.data[DOMAIN][config_entry.entry_id]
    if config_entry.options:
        config.update(config_entry.options)

    if config[CONF_LOCATION] in FMISID_LOCATIONS:
        fmisid = FMISID_VALUES[FMISID_LOCATIONS.index(config[CONF_LOCATION])]
        session = FMIWaterLevelSession(fmisid, config[CONF_HOURS], config[CONF_FORECAST_HOURS], config[CONF_STEP], config[CONF_OVERLAP])
        await hass.async_add_executor_job(session.call_api, True)
        await hass.async_add_executor_job(session.call_api, False)
        async_add_entities(
            [FMIWaterLevelSensor(session, config[CONF_LOCATION], config[CONF_HOURS], config[CONF_FORECAST_HOURS])],
            update_before_add=True
        )


class FMIWaterLevelSensor(Entity):
    _attr_attribution = ATTRIBUTION
    _attr_icon = "mdi:waves-arrow-up"
    _attr_native_unit_of_measurement = "cm"

    def __init__(
            self,
            session: FMIWaterLevelSession,
            location: str,
            hours: int,
            forecast_hours: int
    ):
        super().__init__()
        self._session = session
        self._fmisid = FMISID_VALUES[FMISID_LOCATIONS.index(location)]
        self._location = location
        self._hours = hours
        self._forecast_hours = forecast_hours
        self._state = None
        self._available = True
        self._attrs = {}

    @property
    def name(self) -> str:
        return f"fmi_waterlevel_{self._fmisid}_{self._hours}_{self._forecast_hours}"

    @property
    def unique_id(self) -> str:
        return f"fmi_waterlevel_{self._fmisid}_{self._hours}_{self._forecast_hours}"

    @property
    def available(self) -> bool:
        return self._available

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self._attrs

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        return "cm"

    async def async_update(self):
        try:

            if self._forecast_hours > 0:
                forecast_data = await self.hass.async_add_executor_job(self._session.call_api, True)
            else:
                forecast_data = []

            if self._hours > 0:
                observation_data = await self.hass.async_add_executor_job(self._session.call_api, False)
            else:
                observation_data = []

            observations = []
            forecast = []
            latest_date = None
            latest_waterlevel = None

            for entry in observation_data:
                date = datetime.fromisoformat(entry[0])
                waterlevel = f"{(float(entry[1]) / 10):.1f}"

                if latest_date is None or date > latest_date:
                    latest_date = date
                    latest_waterlevel = waterlevel

                observations.append({ATTR_DATE: date, ATTR_WATERLEVEL: waterlevel})

            for entry in forecast_data:
                date = datetime.fromisoformat(entry[0])
                waterlevel = f"{float(entry[1]):.1f}"
                forecast.append({ATTR_DATE: date, ATTR_WATERLEVEL: waterlevel})

            self._attrs[ATTR_FORECAST] = forecast
            self._attrs[ATTR_OBSERVATIONS] = observations
            self._attrs[ATTR_LATEST_DATE] = latest_date
            self._attrs[ATTR_LATEST_WATERLEVEL] = latest_waterlevel
            self._attrs[ATTR_LOCATION] = self._location
            self._available = True
            self._state = latest_waterlevel

        except ClientError:
            self._available = False
