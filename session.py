import logging
from datetime import datetime, timedelta
from xml.etree import ElementTree
import requests
from requests import ConnectTimeout, RequestException
from .const import API_BASE_URL, USER_AGENT, STORED_QUERY_FORECAST, STORED_QUERY_OBSERVATIONS

_LOGGER = logging.getLogger(__name__)


class FMIWaterLevelException(Exception):
    """Base exception for FMIWaterLevel"""


class FMIWaterLevelSession:
    _timeout: int
    _forecast_hours: int
    _hours: int
    _fmisid: int
    _steps: int
    _overlap: int

    def __init__(self, fmisid: int, hours: int, forecast_hours: int, step: int, overlap: int, timeout=20):
        self._timeout = timeout
        self._forecast_hours = forecast_hours
        self._hours = hours
        self._fmisid = fmisid
        self._step = step
        self._overlap = overlap

    def call_api(self, is_forecast: bool) -> list[list[str | float]]:
        try:
            now = datetime.utcnow()

            if is_forecast is True:
                start_time = now - timedelta(minutes=self._overlap)
                end_time = now + timedelta(hours=self._forecast_hours)
                query = STORED_QUERY_FORECAST
            else:
                start_time = now - timedelta(hours=self._hours)
                end_time = now
                query = STORED_QUERY_OBSERVATIONS

            response = requests.get(
                url=f"{API_BASE_URL}&timestep={self._step}&storedquery_id={query}&starttime={start_time}&endtime={end_time}&fmisid={self._fmisid}",
                headers={
                    "User-Agent": USER_AGENT
                },
                timeout=self._timeout,
            )

            if response.status_code != 200:
                raise FMIWaterLevelException(f"{response.status_code} is not valid")

            else:
                data = []

                namespaces = {
                    "wfs": "http://www.opengis.net/wfs/2.0",
                    "gml": "http://www.opengis.net/gml/3.2",
                    "BsWfs": "http://xml.fmi.fi/schema/wfs/2.0",
                    "xsi": "http://www.w3.org/2001/XMLSchema-instance"
                }

                tree = ElementTree.fromstring(response.text)
                for item in tree.findall("./wfs:member/BsWfs:BsWfsElement", namespaces):
                    name = item.find("./BsWfs:ParameterName", namespaces).text
                    if (is_forecast is True and name == "SeaLevelN2000") or (
                            is_forecast is False and name == "WLEVN2K_PT1S_INSTANT"):
                        data.append([item.find("./BsWfs:Time", namespaces).text,
                                     item.find("./BsWfs:ParameterValue", namespaces).text])

                return data

        except ConnectTimeout as exception:
            raise FMIWaterLevelException("Timeout error") from exception

        except RequestException as exception:
            raise FMIWaterLevelException(f"Communication error {exception}") from exception
