"""Data update coordinator for the ARPA Lombardia integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ArpaLombardiaApiClient, ArpaLombardiaApiClientError, SensorInfo
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ArpaLombardiaDataUpdateCoordinator(DataUpdateCoordinator[dict[int, float | None]]):
    """Coordinator polling the latest values for all sensors of a station."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ArpaLombardiaApiClient,
        idstazione: str,
        sensors: list[SensorInfo],
        scan_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{idstazione}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self.idstazione = idstazione
        self.sensors = sensors

    async def _async_update_data(self) -> dict[int, float | None]:
        """Fetch the latest value for each sensor of the station."""
        try:
            return await self.api.async_get_sensor_values(
                [sensor.idsensore for sensor in self.sensors]
            )
        except ArpaLombardiaApiClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
