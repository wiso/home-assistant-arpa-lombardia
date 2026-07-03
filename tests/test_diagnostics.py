"""Test the ARPA Lombardia diagnostics."""
from unittest.mock import AsyncMock

from custom_components.arpa_lombardia.const import (
    CONF_IDSTAZIONE,
    CONF_STATION_NAME,
    DOMAIN,
)
from custom_components.arpa_lombardia.diagnostics import (
    async_get_config_entry_diagnostics,
)
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_diagnostics(
    hass: HomeAssistant,
    mock_arpa_lombardia_client: AsyncMock,
) -> None:
    """Test the config entry diagnostics."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="700",
        data={CONF_IDSTAZIONE: "700", CONF_STATION_NAME: "Cormano"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["config_entry"]["data"][CONF_IDSTAZIONE] == "700"
    assert diagnostics["config_entry"]["unique_id"] == "**REDACTED**"
    assert {sensor["idsensore"] for sensor in diagnostics["sensors"]} == {101, 102, 103}
    assert diagnostics["coordinator_data"] == {101: 12.5, 102: None, 103: 1.2}
