# ARPA Lombardia for Home Assistant

[![hacs][hacs-badge]][hacs-url]
[![Validate][validate-badge]][validate-url]
[![Test][test-badge]][test-url]

Home Assistant integration for the **air quality monitoring stations of ARPA
Lombardia** (Regione Lombardia open data). Pick a monitoring station and get one
sensor per pollutant it actually measures (PM10, PM2.5, NO₂, O₃, SO₂, CO, …).

Data source: [dati.lombardia.it](https://www.dati.lombardia.it/) (ARPA's
near-real-time dataset, `ykhg-b8rs`). **Please read [How "real-time" is
this?](#how-real-time-is-this-important) below** — the data is hourly, and some
pollutants are reported as 24-hour averages rather than the current
concentration.

## Features

- **UI configuration** — no YAML. Choose a station from a dropdown **sorted by
  distance** from your Home Assistant location, with the distance shown in each
  entry. Stations you have already added are left out of the list.
- **One device per station**, with one sensor per pollutant. Only pollutants
  that actually publish data are created (no permanently *unknown* sensors).
- **Correct device classes and units** — units come straight from the API and a
  device class is applied only when Home Assistant accepts that unit for it.
- Adjustable **scan interval** via the integration options (default 30 minutes;
  ARPA publishes one value per hour).
- **Diagnostics** download support.

## Installation

### HACS (recommended)

1. In HACS, open the three-dot menu → **Custom repositories**.
2. Add `https://github.com/wiso/home-assistant-arpa-lombardia` with category
   **Integration**.
3. Install **ARPA Lombardia**, then restart Home Assistant.

### Manual

Copy `custom_components/arpa_lombardia` into your Home Assistant
`config/custom_components/` directory and restart.

## Configuration

Go to **Settings → Devices & Services → Add Integration**, search for
**ARPA Lombardia**, and select a station. That's it — the pollutant sensors are
created automatically.

To change how often data is fetched: open the integration and click
**Configure**, then set the scan interval (minimum 300 seconds).

## How "real-time" is this? (important)

Home Assistant users usually expect a sensor that updates live, continuously.
**This data is not that.** It is the official regional monitoring network's
published data, and it has two inherent limits worth understanding before you
build automations or alerts on it:

- **Hourly, not continuous.** ARPA's reference-grade stations publish **one value
  per hour** — roughly a bit after the top of each hour. Polling more often gains
  nothing (the scan interval defaults to 30 minutes; the minimum is 300 s).

- **Some pollutants are 24-hour averages, not the current value.** The sensors
  fall into two families that behave very differently:
  - **Gases — NO₂, NO, SO₂, O₃, NOx:** each reading is the **hourly value**. These
    rise and fall through the day as you would expect.
  - **PM10, PM2.5, CO, benzene:** the feed exposes these as a **rolling 24-hour
    average**, not the instantaneous hourly concentration. This is by design (PM
    is regulated as a daily mean). It was verified against the independent EEA
    hourly feed (via OpenAQ): the ARPA value tracks the 24-hour moving average to
    within ~1 µg/m³, while the true hourly concentration can be 3× lower. **So
    these sensors look flat and slow to change — that is the average moving, not a
    stuck sensor or a bug.** An evening drop in real air quality barely moves the
    PM number, because it is averaged over the whole day.

If you specifically need the sharper sub-hourly swing of PM, ARPA's open data
does not expose it — the EEA / OpenAQ hourly feed does, at the cost of a ~2-hour
delay and occasional gaps.

## Notes on the data

- The near-real-time feed only holds the **current day's** measurements, so it is
  briefly empty every night (after midnight, before the day's hourly rows are
  published) and during ARPA maintenance. Rather than flip to `unknown` in those
  gaps, each sensor **keeps showing its last known value** (restored across Home
  Assistant restarts) until a newer reading arrives. A sensor is only `unknown`
  before it has ever reported a value; the reading's age is visible as the
  entity's `last_changed`.
- A value of `-9999` in the source data means *invalid measurement* and is
  discarded (treated as no reading — the last known value is kept).
- Carbon monoxide is published in mg/m³. Home Assistant's `carbon_monoxide`
  device class expects ppm, so CO is exposed as a plain measurement in its
  native mg/m³ unit (no assumption-laden conversion).
- Some pollutants (metals in ng/m³, aggregated NOx, ammonia, …) have no matching
  Home Assistant device class and are shown as generic measurements.

## License

[MIT](LICENSE) © Ruggero Turra

This project is not affiliated with ARPA Lombardia or Regione Lombardia.

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[hacs-url]: https://github.com/hacs/integration
[validate-badge]: https://github.com/wiso/home-assistant-arpa-lombardia/actions/workflows/validate.yml/badge.svg
[validate-url]: https://github.com/wiso/home-assistant-arpa-lombardia/actions/workflows/validate.yml
[test-badge]: https://github.com/wiso/home-assistant-arpa-lombardia/actions/workflows/test.yml/badge.svg
[test-url]: https://github.com/wiso/home-assistant-arpa-lombardia/actions/workflows/test.yml
