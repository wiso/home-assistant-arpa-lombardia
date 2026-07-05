"""Sensor platform for the ARPA Lombardia integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.components.sensor.const import DEVICE_CLASS_UNITS
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

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

# ARPA's feed uses the micro sign (U+00B5, "µ"), but newer Home Assistant
# versions define concentration units (and DEVICE_CLASS_UNITS) using the
# Greek small letter mu (U+03BC, "μ"). Both render identically, so normalize
# before comparing against DEVICE_CLASS_UNITS to avoid silently dropping the
# device class (and falling back to the default icon) on a glyph mismatch.
_MICRO_SIGN = "µ"
_GREEK_MU = "μ"


def _normalize_unit(unit: str) -> str:
    """Normalize micro-sign/Greek-mu variants so unit comparisons are stable."""
    return unit.replace(_MICRO_SIGN, _GREEK_MU)


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
    class is applied only when HA accepts that unit for it (per
    `DEVICE_CLASS_UNITS`); otherwise the sensor keeps its native API unit with
    no device class.
    """
    device_class = _device_class_for(name)
    if device_class is None:
        return None
    allowed_units = DEVICE_CLASS_UNITS.get(device_class)
    if allowed_units is not None and _normalize_unit(unit) not in {
        _normalize_unit(allowed_unit) for allowed_unit in allowed_units
    }:
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


class ArpaLombardiaSensor(ArpaLombardiaEntity, RestoreEntity, SensorEntity):
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
        self._last_value: float | None = None
        device_class = resolve_device_class(
            sensor_info.nometiposensore, sensor_info.unitamisura
        )
        if device_class is not None:
            self._attr_device_class = device_class
        else:
            self._attr_icon = DEFAULT_ICON

    async def async_added_to_hass(self) -> None:
        """Restore the last known value so a restart doesn't lose it."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None or last_state.state in (
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
        ):
            return
        try:
            self._last_value = float(last_state.state)
        except (TypeError, ValueError):
            return

    @property
    def native_value(self) -> float | None:
        """Return the latest value, falling back to the last known one.

        The ARPA NRT feed only holds the current day's data, so every sensor
        reads empty for a few hours after midnight (before the day's rows are
        published) and during ARPA maintenance. Rather than dropping to
        "unknown" in that window, keep showing the last value we read until a
        newer one arrives. The entity only stays "unknown" if no value has ever
        been seen (the timestamp of the reading is visible as the state's
        last_changed, so a genuinely stale sensor is still recognizable).
        """
        value = self.coordinator.data.get(self._idsensore)
        if value is not None:
            self._last_value = value
            return value
        return self._last_value
