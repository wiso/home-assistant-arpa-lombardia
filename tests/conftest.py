"""Common fixtures for the ARPA Lombardia tests."""
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from . import MOCK_SENSORS, MOCK_STATIONS, MOCK_VALUES


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of custom integrations in all tests."""
    yield


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.arpa_lombardia.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_arpa_lombardia_client() -> Generator[AsyncMock, None, None]:
    """Mock the ARPA Lombardia API client used by __init__.py/coordinator."""
    with patch(
        "custom_components.arpa_lombardia.ArpaLombardiaApiClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_get_station_sensors = AsyncMock(return_value=MOCK_SENSORS)
        client.async_get_sensor_ids_with_data = AsyncMock(return_value={101, 102, 103})
        client.async_get_sensor_values = AsyncMock(return_value=MOCK_VALUES)
        yield client


@pytest.fixture
def mock_arpa_lombardia_config_flow_client() -> Generator[AsyncMock, None, None]:
    """Mock the ARPA Lombardia API client used by config_flow.py."""
    with patch(
        "custom_components.arpa_lombardia.config_flow.ArpaLombardiaApiClient",
        autospec=True,
    ) as mock_client_class:
        client = mock_client_class.return_value
        client.async_get_stations = AsyncMock(return_value=MOCK_STATIONS)
        yield client
