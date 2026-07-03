"""Test the ARPA Lombardia integration setup."""
from unittest.mock import AsyncMock

from custom_components.arpa_lombardia.api import ArpaLombardiaApiClientError
from custom_components.arpa_lombardia.const import (
    CONF_IDSTAZIONE,
    CONF_STATION_NAME,
    DOMAIN,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_setup_and_unload_entry(
    hass: HomeAssistant, mock_arpa_lombardia_client: AsyncMock
) -> None:
    """Test a successful setup and unload of a config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="700",
        data={CONF_IDSTAZIONE: "700", CONF_STATION_NAME: "Cormano"},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_entry_not_ready(
    hass: HomeAssistant, mock_arpa_lombardia_client: AsyncMock
) -> None:
    """Test the entry goes into SETUP_RETRY when the sensor list cannot be fetched."""
    mock_arpa_lombardia_client.async_get_station_sensors.side_effect = (
        ArpaLombardiaApiClientError
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="700",
        data={CONF_IDSTAZIONE: "700", CONF_STATION_NAME: "Cormano"},
    )
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
