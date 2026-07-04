# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant custom integration (`custom_components/arpa_lombardia`) that exposes
air quality data from ARPA Lombardia monitoring stations (Regione Lombardia open
data, via the Socrata API at dati.lombardia.it). The user picks a station in the
UI config flow and gets one sensor entity per pollutant that station actually
publishes data for.

## Commands

Setup (installs the pinned Home Assistant version + test/lint deps):
```
./scripts/setup
```

Run Home Assistant locally with this integration symlinked into `config/custom_components/`:
```
./scripts/develop
```
Serves on http://localhost:8123.

Lint (ruff over both the component and tests):
```
./scripts/lint
```

Run tests:
```
pytest tests -v
```
Run a single test file or test:
```
pytest tests/test_sensor.py -v
pytest tests/test_sensor.py::test_name -v
```

CI (`.github/workflows/test.yml`) runs `ruff check custom_components tests` then
`pytest tests -v` on Python 3.14 (required by the pinned `homeassistant`/
`pytest-homeassistant-custom-component` versions — check their `Requires-Python`
before bumping either without also checking the CI Python version) — always
keep both green. `validate.yml` runs
hassfest and the HACS integration validator (brands check intentionally skipped;
see the workflow comment for why).

## Architecture

Data flows through three layers, each with one job:

- **`api.py`** — `ArpaLombardiaApiClient` is the only thing that talks to the
  network. It queries two open Socrata datasets: `STATIONS_URL` (station/sensor
  registry) and `VALUES_URL` (near-real-time measurements). All Socrata errors
  (timeout, HTTP, parse) are normalized into `ArpaLombardiaApiClientError` /
  `ArpaLombardiaApiClientCommunicationError` so callers don't need to know about
  aiohttp.
- **`coordinator.py`** — `ArpaLombardiaDataUpdateCoordinator` (a HA
  `DataUpdateCoordinator`) polls `async_get_sensor_values` for the station's
  sensor list on the configured scan interval and holds the latest
  `{idsensore: value}` dict as its `.data`.
- **`sensor.py`** — one `ArpaLombardiaSensor` entity per `SensorInfo`, reading its
  own value out of the coordinator's data dict.

Key cross-file behaviors worth knowing before touching this code:

- **Sensor filtering happens once, in `__init__.py`.** The station registry
  (`STATIONS_URL`) lists sensors that may never actually appear in the values
  feed (`VALUES_URL`). `async_setup_entry` intersects `async_get_station_sensors`
  against `async_get_sensor_ids_with_data` *before* constructing the coordinator,
  so only sensors that actually publish data become entities — this is what
  prevents permanently-`unknown` sensors. If you're debugging a "missing sensor"
  report, check this filter first, not the coordinator.
- **Device class is applied only when the API's unit matches what HA expects for
  it** (`sensor.py: resolve_device_class`, checked dynamically against HA's
  `DEVICE_CLASS_UNITS`). Pollutant name → device class mapping is split into
  exact-match gases (`GAS_DEVICE_CLASSES`) and substring-matched particulates
  (PM10/PM2.5, since the API's name for these varies). `DEVICE_CLASS_UNITS` has
  changed across HA versions (e.g. CO's allowed units expanded from just
  ppm/ppb to also include mg/m³ and μg/m³ by 2026.7) — a `pytest` failure on the
  CO/PM assertions after a HA version bump likely means the test's expected
  unit set is stale, not that `resolve_device_class` broke.
- **`-9999` means invalid measurement** (`const.INVALID_VALUE`), normalized to
  `None` in `api._async_get_latest_value` — never surface the raw sentinel value
  to entities.
- **Station selection is distance-sorted** in `config_flow.py` using
  `homeassistant.util.location.distance` against `hass.config.latitude/longitude`;
  stations with missing lat/lng sort last alphabetically rather than being
  dropped.
- **One device per station, one entry per config flow** — uniqueness is enforced
  on `idstazione` via `async_set_unique_id` / `_abort_if_unique_id_configured`.
- Changing the scan interval (options flow, `CONF_SCAN_INTERVAL`, min
  `MIN_SCAN_INTERVAL` = 300s) triggers a full reload via
  `_async_update_listener` → `async_reload`, not a live coordinator update.

## Tests

`tests/__init__.py` defines shared `MOCK_STATIONS` / `MOCK_SENSORS` / `MOCK_VALUES`
fixtures used across test files. `tests/conftest.py` patches
`ArpaLombardiaApiClient` at two different import paths depending on what's under
test — `custom_components.arpa_lombardia.ArpaLombardiaApiClient` for
init/coordinator tests, `custom_components.arpa_lombardia.config_flow.ArpaLombardiaApiClient`
for config flow tests. Match that pattern for new tests rather than patching
`api.ArpaLombardiaApiClient` directly, or the mock won't intercept the actual
call site.
