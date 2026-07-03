"""Sensor platform for the ARPA Lombardia integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.components.sensor.const import DEVICE_CLASS_UNITS
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import SensorInfo
from .const import CONF_STATION_NAME, DOMAIN
from .coordinator import ArpaLombardiaDataUpdateCoordinator
from .entity import ArpaLombardiaEntity

# Map ARPA Lombardia gas pollutants ("nometiposensore") to HA device classes.
# Particulate matter is matched separately by substring, as its name varies
# (e.g. "PM10 (SM2005)", "Particelle sospese PM2.5").
GAS_DEVICE_CLASSES: dict[str, SensorDeviceClass] = {
    "Biossido di Azoto": SensorDeviceClass.NITROGEN_DIOXIDE,
    "Monossido di Azoto": SensorDeviceClass.NITROGEN_MONOXIDE,
    "Ozono": SensorDeviceClass.OZONE,
    "Biossido di Zolfo": SensorDeviceClass.SULPHUR_DIOXIDE,
    "Monossido di Carbonio": SensorDeviceClass.CO,
    "Benzene": SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
}

DEFAULT_ICON = "mdi:molecule"


def _device_class_for(name: str) -> SensorDeviceClass | None:
    """Return the device class for a pollutant name, ignoring the unit."""
    if "PM10" in name:
        return SensorDeviceClass.PM10
    if "PM2.5" in name or "PM2,5" in name:
        return SensorDeviceClass.PM25
    return GAS_DEVICE_CLASSES.get(name)


def resolve_device_class(name: str, unit: str) -> SensorDeviceClass | None:
    """Return the device class only if the API unit is valid for it.

    ARPA reports pollutants in mass concentration (µg/m³, mg/m³, ng/m³). A device
    class is applied only when HA accepts that unit for it; otherwise the sensor
    keeps its native API unit with no device class. This avoids, for example,
    forcing the CO device class (which expects ppm) onto a mg/m³ value.
    """
    device_class = _device_class_for(name)
    if device_class is None:
        return None
    allowed_units = DEVICE_CLASS_UNITS.get(device_class)
    if allowed_units is not None and unit not in allowed_units:
        return None
    return device_class


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ARPA Lombardia sensors from a config entry."""
    coordinator: ArpaLombardiaDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]
    station_name = config_entry.data[CONF_STATION_NAME]
    async_add_entities(
        ArpaLombardiaSensor(coordinator, station_name, sensor)
        for sensor in coordinator.sensors
    )


class ArpaLombardiaSensor(ArpaLombardiaEntity, SensorEntity):
    """Representation of a single pollutant sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: ArpaLombardiaDataUpdateCoordinator,
        station_name: str,
        sensor_info: SensorInfo,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, station_name)
        self._idsensore = sensor_info.idsensore
        self._attr_unique_id = f"{coordinator.idstazione}_{sensor_info.idsensore}"
        self._attr_name = sensor_info.nometiposensore
        self._attr_native_unit_of_measurement = sensor_info.unitamisura
        device_class = resolve_device_class(
            sensor_info.nometiposensore, sensor_info.unitamisura
        )
        if device_class is not None:
            self._attr_device_class = device_class
        else:
            self._attr_icon = DEFAULT_ICON

    @property
    def native_value(self) -> float | None:
        """Return the latest value for this sensor."""
        return self.coordinator.data.get(self._idsensore)
