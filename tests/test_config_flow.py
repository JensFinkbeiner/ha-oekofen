"""Tests for the config flow (100 % coverage required)."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.oekofen.api import (
    OekofenAuthError,
    OekofenBusyError,
    OekofenConnectionError,
    OekofenData,
    OekofenParseError,
)
from custom_components.oekofen.const import DOMAIN

from .conftest import TEST_HOST, TEST_PASSWORD, TEST_PORT, load_data

USER_INPUT = {
    CONF_HOST: f" {TEST_HOST} ",
    CONF_PORT: TEST_PORT,
    CONF_PASSWORD: TEST_PASSWORD,
}


async def test_user_flow_creates_entry(
    hass: HomeAssistant, mock_client: MagicMock
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ÖkoFEN Pellematic"
    assert result["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_PORT: TEST_PORT,
        CONF_PASSWORD: TEST_PASSWORD,
    }
    first_call = mock_client.async_get_data.await_args_list[0]
    assert first_call.kwargs == {"refresh_metadata": True}


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (OekofenAuthError("x"), "invalid_auth"),
        (OekofenBusyError("x"), "busy"),
        (OekofenConnectionError("x"), "cannot_connect"),
        (OekofenParseError("x"), "invalid_answer"),
        (RuntimeError("x"), "unknown"),
        (None, "no_boiler"),
    ],
)
async def test_user_flow_errors_and_recovery(
    hass: HomeAssistant,
    mock_client: MagicMock,
    side_effect: Exception | None,
    error: str,
) -> None:
    if side_effect is None:
        mock_client.async_get_data.return_value = OekofenData()
    else:
        mock_client.async_get_data.side_effect = side_effect
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_client.async_get_data.side_effect = None
    mock_client.async_get_data.return_value = load_data()
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_aborts_when_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    mock_client.async_get_data.assert_not_awaited()


async def test_reauth_flow(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_client: MagicMock
) -> None:
    result = await init_integration.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    mock_client.async_get_data.side_effect = OekofenAuthError("x")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "wrong"}
    )
    assert result["errors"] == {"base": "invalid_auth"}

    mock_client.async_get_data.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "new-pw"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert init_integration.data[CONF_PASSWORD] == "new-pw"


async def test_reconfigure_flow(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_client: MagicMock
) -> None:
    result = await init_integration.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"

    mock_client.async_get_data.side_effect = OekofenConnectionError("x")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.0.2.11", CONF_PORT: 4322}
    )
    assert result["errors"] == {"base": "cannot_connect"}

    mock_client.async_get_data.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: " 192.0.2.11 ", CONF_PORT: 4322}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert init_integration.data[CONF_HOST] == "192.0.2.11"
    assert init_integration.data[CONF_PORT] == 4322
    assert init_integration.data[CONF_PASSWORD] == TEST_PASSWORD


async def test_reconfigure_to_existing_entry_aborts(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_client: MagicMock
) -> None:
    other = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.0.2.12", CONF_PORT: 4321, CONF_PASSWORD: "x"},
    )
    other.add_to_hass(hass)
    result = await init_integration.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.0.2.12", CONF_PORT: 4321}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_client: MagicMock
) -> None:
    result = await hass.config_entries.options.async_init(init_integration.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SCAN_INTERVAL: 120,
            "nominal_kw": 15,
            "efficiency_percent": 90,
            "heating_value": 5,
            "calibration": 1.1,
        },
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert init_integration.options == {
        CONF_SCAN_INTERVAL: 120,
        "nominal_kw": 15.0,
        "efficiency_percent": 90.0,
        "heating_value": 5.0,
        "calibration": 1.1,
    }
    coordinator = init_integration.runtime_data.coordinator
    assert coordinator.update_interval is not None
    assert coordinator.update_interval.total_seconds() == 120
    model = coordinator.energy_model
    assert (model.nominal_kw, model.efficiency, model.heating_value_kwh_per_kg) == (
        15.0,
        0.9,
        5.0,
    )
    assert model.calibration == 1.1


async def test_password_not_sent_back_after_error(
    hass: HomeAssistant, mock_client: MagicMock
) -> None:
    mock_client.async_get_data.side_effect = OekofenConnectionError("x")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    schema = result["data_schema"].schema
    suggested = {
        str(key): (key.description or {}).get("suggested_value") for key in schema
    }
    assert str(suggested[CONF_HOST]).strip() == TEST_HOST
    assert suggested[CONF_PASSWORD] is None
