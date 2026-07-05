"""Config flow for the ARPA Lombardia integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.util.location import distance

from .api import ArpaLombardiaApiClient, ArpaLombardiaApiClientError, StationInfo
from .const import (
    CONF_IDSTAZIONE,
    CONF_STATION_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class ArpaLombardiaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ARPA Lombardia."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._stations: dict[str, StationInfo] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user pick a monitoring station."""
        if self._stations is None:
            client = ArpaLombardiaApiClient(async_get_clientsession(self.hass))
            try:
                self._stations = await client.async_get_stations()
            except ArpaLombardiaApiClientError:
                _LOGGER.exception("Cannot retrieve the list of stations")
                return self.async_abort(reason="cannot_connect")
        stations = self._stations

        if user_input is not None:
            idstazione = user_input[CONF_IDSTAZIONE]
            station = stations[idstazione]
            await self.async_set_unique_id(idstazione)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=station.nomestazione,
                data={
                    CONF_IDSTAZIONE: idstazione,
                    CONF_STATION_NAME: station.nomestazione,
                },
            )

        home_lat = self.hass.config.latitude
        home_lon = self.hass.config.longitude

        def station_distance(station: StationInfo) -> float | None:
            """Distance in meters from home, or None if not computable."""
            if station.latitude is None or station.longitude is None:
                return None
            return distance(home_lat, home_lon, station.latitude, station.longitude)

        def sort_key(station: StationInfo) -> tuple[float, str]:
            dist = station_distance(station)
            # Stations without a distance sort last, then alphabetically.
            return (dist if dist is not None else float("inf"), station.nomestazione)

        def label(station: StationInfo) -> str:
            dist = station_distance(station)
            if dist is None:
                return f"{station.nomestazione} ({station.comune})"
            return f"{station.nomestazione} ({station.comune}) — {dist / 1000:.1f} km"

        # Don't offer stations that already have a config entry (unique_id is
        # the idstazione), so the dropdown only lists ones the user can add.
        configured_ids = self._async_current_ids()
        available = [
            station
            for station in stations.values()
            if station.idstazione not in configured_ids
        ]
        if not available:
            return self.async_abort(reason="no_stations")

        options = [
            SelectOptionDict(value=station.idstazione, label=label(station))
            for station in sorted(available, key=sort_key)
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_IDSTAZIONE): SelectSelector(
                    SelectSelectorConfig(
                        options=options, mode=SelectSelectorMode.DROPDOWN
                    )
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ArpaLombardiaOptionsFlow:
        """Create the options flow."""
        return ArpaLombardiaOptionsFlow()


class ArpaLombardiaOptionsFlow(config_entries.OptionsFlow):
    """Handle options for the ARPA Lombardia integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the scan interval option."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(int, vol.Range(min=MIN_SCAN_INTERVAL)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
