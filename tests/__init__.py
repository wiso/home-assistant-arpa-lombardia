"""Tests for the ARPA Lombardia integration."""
from custom_components.arpa_lombardia.api import SensorInfo, StationInfo

MOCK_STATIONS = {
    "700": StationInfo(
        idstazione="700",
        nomestazione="Cormano",
        comune="Cormano",
        provincia="MI",
        latitude=45.54,
        longitude=9.16,
    ),
    "701": StationInfo(
        idstazione="701",
        nomestazione="Milano - Pascal Città Studi",
        comune="Milano",
        provincia="MI",
        latitude=45.48,
        longitude=9.23,
    ),
}

MOCK_SENSORS = [
    SensorInfo(
        idsensore=101, nometiposensore="Particelle sospese PM2.5", unitamisura="µg/m³"
    ),
    SensorInfo(idsensore=102, nometiposensore="Ozono", unitamisura="µg/m³"),
    SensorInfo(
        idsensore=103, nometiposensore="Monossido di Carbonio", unitamisura="mg/m³"
    ),
]

MOCK_VALUES = {101: 12.5, 102: None, 103: 1.2}
