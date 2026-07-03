"""Constants for the ARPA Lombardia integration."""
from typing import Final

DOMAIN = "arpa_lombardia"

CONF_IDSTAZIONE = "idstazione"
CONF_STATION_NAME = "station_name"

DEFAULT_SCAN_INTERVAL = 1800
MIN_SCAN_INTERVAL = 300

STATIONS_URL: Final = "https://www.dati.lombardia.it/resource/ib47-atvt.json"
VALUES_URL: Final = "https://www.dati.lombardia.it/resource/ykhg-b8rs.json"

INVALID_VALUE = -9999
