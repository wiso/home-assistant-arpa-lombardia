"""API client for the ARPA Lombardia open data portal."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging

import aiohttp

from .const import INVALID_VALUE, STATIONS_URL, VALUES_URL

_LOGGER = logging.getLogger(__name__)

TIMEOUT = 20


class ArpaLombardiaApiClientError(Exception):
    """Base error for the ARPA Lombardia API client."""


class ArpaLombardiaApiClientCommunicationError(ArpaLombardiaApiClientError):
    """Error raised when the API cannot be reached or returns bad data."""


@dataclass
class StationInfo:
    """A monitoring station."""

    idstazione: str
    nomestazione: str
    comune: str
    provincia: str
    latitude: float | None = None
    longitude: float | None = None


def _parse_float(value: str | None) -> float | None:
    """Parse a coordinate string, returning None when missing or not numeric."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass
class SensorInfo:
    """A pollutant sensor belonging to a station."""

    idsensore: int
    nometiposensore: str
    unitamisura: str


class ArpaLombardiaApiClient:
    """Client to retrieve station, sensor and measurement data."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the client."""
        self._session = session

    async def _get_json(self, url: str, params: dict[str, str]) -> list[dict]:
        """Perform a GET request against a Socrata dataset and return the JSON body."""
        _LOGGER.debug("Fetching %s with params %s", url, params)
        try:
            async with asyncio.timeout(TIMEOUT):
                response = await self._session.get(url, params=params)
                response.raise_for_status()
                return await response.json()
        except TimeoutError as err:
            raise ArpaLombardiaApiClientCommunicationError(
                f"Timeout while fetching {url}"
            ) from err
        except aiohttp.ClientError as err:
            raise ArpaLombardiaApiClientCommunicationError(
                f"Error fetching {url}: {err}"
            ) from err
        except (KeyError, TypeError, ValueError) as err:
            raise ArpaLombardiaApiClientCommunicationError(
                f"Error parsing response from {url}: {err}"
            ) from err

    async def async_get_stations(self) -> dict[str, StationInfo]:
        """Return the active monitoring stations, keyed by idstazione."""
        params = {
            "$select": "idstazione,nomestazione,comune,provincia,lat,lng",
            "$where": "storico='N'",
            "$group": "idstazione,nomestazione,comune,provincia,lat,lng",
            "$limit": "1000",
        }
        rows = await self._get_json(STATIONS_URL, params)
        return {
            row["idstazione"]: StationInfo(
                idstazione=row["idstazione"],
                nomestazione=row["nomestazione"],
                comune=row.get("comune", ""),
                provincia=row.get("provincia", ""),
                latitude=_parse_float(row.get("lat")),
                longitude=_parse_float(row.get("lng")),
            )
            for row in rows
        }

    async def async_get_station_sensors(self, idstazione: str) -> list[SensorInfo]:
        """Return the active sensors for a given station."""
        params = {
            "$select": "idsensore,nometiposensore,unitamisura",
            "$where": f"idstazione='{idstazione}' AND storico='N'",
            "$limit": "100",
        }
        rows = await self._get_json(STATIONS_URL, params)
        return [
            SensorInfo(
                idsensore=int(row["idsensore"]),
                nometiposensore=row["nometiposensore"],
                unitamisura=row.get("unitamisura", ""),
            )
            for row in rows
        ]

    async def async_get_sensor_ids_with_data(
        self, idsensore_list: list[int]
    ) -> set[int]:
        """Return the subset of sensor ids that actually publish data in the NRT feed.

        The station registry marks sensors as active even when they never appear in
        the values dataset, which would create permanently "unknown" entities.
        """
        if not idsensore_list:
            return set()
        in_list = ",".join(f"'{idsensore}'" for idsensore in idsensore_list)
        params = {
            "$select": "idsensore",
            "$where": f"idsensore in ({in_list})",
            "$group": "idsensore",
            "$limit": "1000",
        }
        rows = await self._get_json(VALUES_URL, params)
        return {int(row["idsensore"]) for row in rows}

    async def async_get_sensor_values(
        self, idsensore_list: list[int]
    ) -> dict[int, float | None]:
        """Return the latest value for each sensor id, in parallel."""
        results = await asyncio.gather(
            *(self._async_get_latest_value(idsensore) for idsensore in idsensore_list)
        )
        return dict(zip(idsensore_list, results, strict=True))

    async def _async_get_latest_value(self, idsensore: int) -> float | None:
        """Return the latest valid value for a single sensor."""
        params = {
            "$select": "valore",
            "$where": f"idsensore='{idsensore}'",
            "$order": "data DESC",
            "$limit": "1",
        }
        rows = await self._get_json(VALUES_URL, params)
        if not rows:
            return None
        value = float(rows[0]["valore"])
        if value == INVALID_VALUE:
            return None
        return value
