"""Test the ARPA Lombardia API client."""
import pytest

from custom_components.arpa_lombardia.api import (
    ArpaLombardiaApiClient,
    ArpaLombardiaApiClientCommunicationError,
)
from custom_components.arpa_lombardia.const import STATIONS_URL, VALUES_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker


async def test_get_stations(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Stations are parsed, and missing coordinates become None."""
    aioclient_mock.get(
        STATIONS_URL,
        json=[
            {
                "idstazione": "700",
                "nomestazione": "Cormano",
                "comune": "Cormano",
                "provincia": "MI",
                "lat": "45.54",
                "lng": "9.16",
            },
            {
                "idstazione": "701",
                "nomestazione": "Senza coordinate",
                "comune": "X",
                "provincia": "MI",
            },
        ],
    )
    client = ArpaLombardiaApiClient(async_get_clientsession(hass))
    stations = await client.async_get_stations()

    assert set(stations) == {"700", "701"}
    assert stations["700"].latitude == 45.54
    assert stations["700"].longitude == 9.16
    assert stations["701"].latitude is None
    assert stations["701"].longitude is None


async def test_get_station_sensors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Sensors of a station are parsed with idsensore coerced to int."""
    aioclient_mock.get(
        STATIONS_URL,
        json=[
            {
                "idsensore": "101",
                "nometiposensore": "Ozono",
                "unitamisura": "µg/m³",
            }
        ],
    )
    client = ArpaLombardiaApiClient(async_get_clientsession(hass))
    sensors = await client.async_get_station_sensors("700")

    assert len(sensors) == 1
    assert sensors[0].idsensore == 101
    assert sensors[0].nometiposensore == "Ozono"
    assert sensors[0].unitamisura == "µg/m³"


async def test_get_sensor_values(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Latest values are returned; -9999 and empty responses become None."""
    aioclient_mock.get(
        VALUES_URL, params={"$where": "idsensore='101'"}, json=[{"valore": "12.5"}]
    )
    aioclient_mock.get(
        VALUES_URL, params={"$where": "idsensore='102'"}, json=[{"valore": "-9999"}]
    )
    aioclient_mock.get(VALUES_URL, params={"$where": "idsensore='103'"}, json=[])

    client = ArpaLombardiaApiClient(async_get_clientsession(hass))
    values = await client.async_get_sensor_values([101, 102, 103])

    assert values == {101: 12.5, 102: None, 103: None}


async def test_get_sensor_ids_with_data(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Only sensor ids present in the values dataset are returned."""
    aioclient_mock.get(
        VALUES_URL,
        json=[{"idsensore": "101"}, {"idsensore": "102"}],
    )
    client = ArpaLombardiaApiClient(async_get_clientsession(hass))

    ids = await client.async_get_sensor_ids_with_data([101, 102, 103])

    assert ids == {101, 102}


async def test_get_sensor_ids_with_data_empty(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """An empty input list returns an empty set without any request."""
    client = ArpaLombardiaApiClient(async_get_clientsession(hass))

    assert await client.async_get_sensor_ids_with_data([]) == set()
    assert aioclient_mock.call_count == 0


async def test_http_error_raises(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """An HTTP error is surfaced as a communication error."""
    aioclient_mock.get(STATIONS_URL, status=500)
    client = ArpaLombardiaApiClient(async_get_clientsession(hass))

    with pytest.raises(ArpaLombardiaApiClientCommunicationError):
        await client.async_get_stations()
