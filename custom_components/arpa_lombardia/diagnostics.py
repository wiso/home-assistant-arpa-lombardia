"""Diagnostics support for ARPA Lombardia."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ArpaLombardiaDataUpdateCoordinator

TO_REDACT = {CONF_UNIQUE_ID}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: ArpaLombardiaDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    return {
        "config_entry": async_redact_data(config_entry.as_dict(), TO_REDACT),
        "sensors": [asdict(sensor) for sensor in coordinator.sensors],
        "coordinator_data": coordinator.data,
    }
