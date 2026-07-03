"""Base entity for the ARPA Lombardia integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ArpaLombardiaDataUpdateCoordinator


class ArpaLombardiaEntity(CoordinatorEntity[ArpaLombardiaDataUpdateCoordinator]):
    """Base entity tying all sensors of a station to the same device."""

    _attr_has_entity_name = True
    _attr_attribution = "Data provided by ARPA Lombardia"

    def __init__(
        self, coordinator: ArpaLombardiaDataUpdateCoordinator, station_name: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.idstazione)},
            name=station_name,
            manufacturer="ARPA Lombardia",
        )
