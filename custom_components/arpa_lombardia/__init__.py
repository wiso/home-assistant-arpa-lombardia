"""The ARPA Lombardia integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ArpaLombardiaApiClient, ArpaLombardiaApiClientError
from .const import CONF_IDSTAZIONE, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import ArpaLombardiaDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ARPA Lombardia from a config entry."""
    client = ArpaLombardiaApiClient(async_get_clientsession(hass))

    try:
        sensors = await client.async_get_station_sensors(entry.data[CONF_IDSTAZIONE])
        ids_with_data = await client.async_get_sensor_ids_with_data(
            [sensor.idsensore for sensor in sensors]
        )
    except ArpaLombardiaApiClientError as err:
        raise ConfigEntryNotReady(
            f"Cannot retrieve sensors for station {entry.data[CONF_IDSTAZIONE]}"
        ) from err

    # Keep only sensors that actually publish data, to avoid permanently
    # "unknown" entities for sensors the registry lists but the feed omits.
    #
    # The NRT values feed only holds the current day's data and is periodically
    # empty for *every* station — e.g. just after midnight before the new day's
    # hourly rows are published, or during ARPA maintenance. If HA (re)starts in
    # such a window, the filter would drop every sensor and we'd create no
    # entities at all, and they'd never reappear until the entry is reloaded
    # while the feed happens to be populated. Fall back to the full registry
    # list so the entities still exist (they simply stay "unknown" until the
    # feed refills).
    sensors_with_data = [
        sensor for sensor in sensors if sensor.idsensore in ids_with_data
    ]
    sensors = sensors_with_data or sensors

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = ArpaLombardiaDataUpdateCoordinator(
        hass, client, entry.data[CONF_IDSTAZIONE], sensors, scan_interval
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
