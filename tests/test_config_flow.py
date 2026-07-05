"""Test the ARPA Lombardia config flow."""
from unittest.mock import AsyncMock

from homeassistant import config_entries
from custom_components.arpa_lombardia.api import ArpaLombardiaApiClientError
from custom_components.arpa_lombardia.const import (
    CONF_IDSTAZIONE,
    CONF_STATION_NAME,
    DOMAIN,
)
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_form(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_arpa_lombardia_config_flow_client: AsyncMock,
) -> None:
    """Test we get the form and can create an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_IDSTAZIONE: "700"}
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Cormano"
    assert result["data"] == {
        CONF_IDSTAZIONE: "700",
        CONF_STATION_NAME: "Cormano",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_sorted_by_distance(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_arpa_lombardia_config_flow_client: AsyncMock,
) -> None:
    """Test stations are ordered by distance from home with the distance shown."""
    # Home right on top of the Milano station (701).
    hass.config.latitude = 45.48
    hass.config.longitude = 9.23

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    schema = result["data_schema"].schema
    selector = next(iter(schema.values()))
    options = selector.config["options"]

    # Nearest station (Milano, 701) comes first.
    assert options[0]["value"] == "701"
    assert options[1]["value"] == "700"
    # The label includes the distance in km.
    assert "km" in options[0]["label"]


async def test_form_cannot_connect(
    hass: HomeAssistant,
    mock_arpa_lombardia_config_flow_client: AsyncMock,
) -> None:
    """Test we abort when the station list cannot be retrieved."""
    mock_arpa_lombardia_config_flow_client.async_get_stations.side_effect = (
        ArpaLombardiaApiClientError
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_form_hides_configured_stations(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_arpa_lombardia_config_flow_client: AsyncMock,
) -> None:
    """Already-configured stations are not offered in the dropdown."""
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="700",
        data={CONF_IDSTAZIONE: "700", CONF_STATION_NAME: "Cormano"},
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    schema = result["data_schema"].schema
    selector = next(iter(schema.values()))
    values = [option["value"] for option in selector.config["options"]]
    assert "700" not in values
    assert "701" in values


async def test_form_no_stations_left(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    mock_arpa_lombardia_config_flow_client: AsyncMock,
) -> None:
    """The flow aborts when every station is already configured."""
    for idstazione, name in (("700", "Cormano"), ("701", "Milano")):
        MockConfigEntry(
            domain=DOMAIN,
            unique_id=idstazione,
            data={CONF_IDSTAZIONE: idstazione, CONF_STATION_NAME: name},
        ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_stations"


async def test_options_flow(
    hass: HomeAssistant,
    mock_arpa_lombardia_client: AsyncMock,
) -> None:
    """Test updating the scan interval via the options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="700",
        data={CONF_IDSTAZIONE: "700", CONF_STATION_NAME: "Cormano"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 600}
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SCAN_INTERVAL] == 600
