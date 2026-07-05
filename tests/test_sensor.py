"""Test the ARPA Lombardia sensors."""
from unittest.mock import AsyncMock

from custom_components.arpa_lombardia.const import (
    CONF_IDSTAZIONE,
    CONF_STATION_NAME,
    DOMAIN,
)
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
)

PM25_ENTITY_ID = "sensor.cormano_particelle_sospese_pm2_5"


async def test_sensors(
    hass: HomeAssistant, mock_arpa_lombardia_client: AsyncMock
) -> None:
    """Test the sensors created for a station, including an invalid reading."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="700",
        data={CONF_IDSTAZIONE: "700", CONF_STATION_NAME: "Cormano"},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    # PM2.5 is classified despite its ARPA-specific name and carries attribution.
    pm25_entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, "700_101")
    assert pm25_entity_id is not None
    pm25_state = hass.states.get(pm25_entity_id)
    assert pm25_state.state == "12.5"
    assert (
        pm25_state.attributes["unit_of_measurement"]
        == CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
    )
    assert pm25_state.attributes["device_class"] == "pm25"
    assert pm25_state.attributes[ATTR_ATTRIBUTION] == "Data provided by ARPA Lombardia"

    # An invalid (-9999) reading is exposed as unknown.
    ozono_entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, "700_102")
    assert ozono_entity_id is not None
    ozono_state = hass.states.get(ozono_entity_id)
    assert ozono_state.state == STATE_UNKNOWN

    # CO is reported in mg/m³. HA 2026.7+ accepts this unit for the CO device
    # class (older versions only accepted ppm/ppb), so it now gets classified
    # while keeping its native unit (no unit conversion).
    co_entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, "700_103")
    assert co_entity_id is not None
    co_state = hass.states.get(co_entity_id)
    assert co_state.state == "1.2"
    assert co_state.attributes["unit_of_measurement"] == "mg/m³"
    assert co_state.attributes["device_class"] == "carbon_monoxide"


async def test_keeps_last_value_when_feed_empty(
    hass: HomeAssistant, mock_arpa_lombardia_client: AsyncMock
) -> None:
    """A momentarily empty feed keeps the last value instead of going unknown."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="700",
        data={CONF_IDSTAZIONE: "700", CONF_STATION_NAME: "Cormano"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(PM25_ENTITY_ID).state == "12.5"

    # The NRT feed empties (e.g. just after midnight): every sensor reads None.
    mock_arpa_lombardia_client.async_get_sensor_values.return_value = {
        101: None,
        102: None,
        103: None,
    }
    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # The last known value is kept rather than flipping to unknown.
    assert hass.states.get(PM25_ENTITY_ID).state == "12.5"

    # A newer reading replaces it once the feed publishes again.
    mock_arpa_lombardia_client.async_get_sensor_values.return_value = {
        101: 20.0,
        102: None,
        103: None,
    }
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(PM25_ENTITY_ID).state == "20.0"


async def test_restores_last_value_after_restart(
    hass: HomeAssistant, mock_arpa_lombardia_client: AsyncMock
) -> None:
    """A restart during an empty-feed window restores the last value."""
    # Feed is empty from the first refresh (e.g. HA restarted overnight).
    mock_arpa_lombardia_client.async_get_sensor_values.return_value = {
        101: None,
        102: None,
        103: None,
    }
    mock_restore_cache(hass, (State(PM25_ENTITY_ID, "9.9"),))

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="700",
        data={CONF_IDSTAZIONE: "700", CONF_STATION_NAME: "Cormano"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(PM25_ENTITY_ID).state == "9.9"


async def test_sensors_without_data_are_skipped(
    hass: HomeAssistant, mock_arpa_lombardia_client: AsyncMock
) -> None:
    """Sensors that don't publish data in the feed get no entity."""
    # The registry lists 3 sensors, but only 101 and 102 have data.
    mock_arpa_lombardia_client.async_get_sensor_ids_with_data.return_value = {101, 102}

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="700",
        data={CONF_IDSTAZIONE: "700", CONF_STATION_NAME: "Cormano"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, "700_101") is not None
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, "700_102") is not None
    # The sensor without data (103) is not created.
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, "700_103") is None
