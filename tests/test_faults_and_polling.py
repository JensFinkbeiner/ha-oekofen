"""Tests for faults, repair issue, robust polling, firmware, model, units, counters."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, issue_registry as ir
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.oekofen.api import (
    OekofenBusyError,
    OekofenConnectionError,
    OekofenData,
    OekofenError,
    OekofenFault,
)
from custom_components.oekofen.api.models import FieldMeta
from custom_components.oekofen.const import DOMAIN
from custom_components.oekofen.coordinator import fault_issue_id

from .conftest import load_data

FAULT = "binary_sensor.okofen_pellematic_fault"
FAULT_MESSAGE = "sensor.okofen_pellematic_fault_message"
BOILER_TEMP = "sensor.okofen_pellematic_boiler_temperature"
STARTS = "sensor.okofen_pellematic_burner_starts"


def with_fault() -> OekofenData:
    """Invented fault in the format of the boiler ("date|text [code]")."""
    data = load_data()
    data.sections["system"]["L_errors"] = 1
    data.faults = [
        OekofenFault(
            raw="21.11.2026 10:00|Zuendung fehlgeschlagen [2010]",
            date="21.11.2026 10:00",
            text="Zuendung fehlgeschlagen",
            code=2010,
        )
    ]
    return data


async def tick(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float
) -> None:
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_fault_entities_and_repair_issue(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
    issue_registry: ir.IssueRegistry,
) -> None:
    issue_id = fault_issue_id(init_integration)
    assert hass.states.get(FAULT).state == STATE_OFF
    assert hass.states.get(FAULT_MESSAGE).state == STATE_UNKNOWN
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None

    mock_client.async_get_data.return_value = with_fault()
    await tick(hass, freezer, 61)
    assert hass.states.get(FAULT).state == STATE_ON
    state = hass.states.get(FAULT_MESSAGE)
    assert state.state == "Zuendung fehlgeschlagen [2010]"
    assert state.attributes["faults"] == [
        {"date": "21.11.2026 10:00", "text": "Zuendung fehlgeschlagen", "code": 2010}
    ]
    issue = issue_registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_placeholders == {
        "fault": "Zuendung fehlgeschlagen",
        "code": "2010",
        "count": "1",
    }

    mock_client.async_get_data.return_value = load_data()
    await tick(hass, freezer, 61)
    assert hass.states.get(FAULT).state == STATE_OFF
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None


async def test_fault_without_code_and_error_count_only(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
    issue_registry: ir.IssueRegistry,
) -> None:
    data = with_fault()
    data.faults = [
        OekofenFault(raw="Saugturbine", date=None, text="Saugturbine", code=None)
    ]
    mock_client.async_get_data.return_value = data
    await tick(hass, freezer, 61)
    assert hass.states.get(FAULT_MESSAGE).state == "Saugturbine"
    issue = issue_registry.async_get_issue(DOMAIN, fault_issue_id(init_integration))
    assert issue is not None
    assert issue.translation_placeholders["code"] == "-"

    data = load_data()
    data.sections["system"]["L_errors"] = 2  # counter only, no texts
    mock_client.async_get_data.return_value = data
    await tick(hass, freezer, 61)
    assert hass.states.get(FAULT).state == STATE_ON
    assert hass.states.get(FAULT_MESSAGE).state == STATE_UNKNOWN


async def test_issue_removed_on_unload(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
    issue_registry: ir.IssueRegistry,
) -> None:
    mock_client.async_get_data.return_value = with_fault()
    await tick(hass, freezer, 61)
    assert issue_registry.async_get_issue(DOMAIN, fault_issue_id(init_integration))
    await hass.config_entries.async_unload(init_integration.entry_id)
    await hass.async_block_till_done()
    assert (
        issue_registry.async_get_issue(DOMAIN, fault_issue_id(init_integration)) is None
    )


async def test_single_busy_keeps_values(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    mock_client.async_get_data.side_effect = OekofenBusyError("x")
    await tick(hass, freezer, 61)
    assert hass.states.get(BOILER_TEMP).state != STATE_UNAVAILABLE
    await tick(hass, freezer, 61)
    assert hass.states.get(BOILER_TEMP).state == STATE_UNAVAILABLE


async def test_backoff_and_reset(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    coordinator = init_integration.runtime_data.coordinator
    mock_client.async_get_data.side_effect = OekofenConnectionError("x")
    intervals = []
    for _ in range(7):
        await tick(hass, freezer, coordinator.update_interval.total_seconds() + 1)
        intervals.append(coordinator.update_interval.total_seconds())
    # first retry at the normal interval, then doubling up to 10 min
    assert intervals == [60, 120, 240, 480, 600, 600, 600]

    mock_client.async_get_data.side_effect = None
    await tick(hass, freezer, 601)
    assert coordinator.update_interval.total_seconds() == 60
    assert hass.states.get(BOILER_TEMP).state != STATE_UNAVAILABLE


@pytest.mark.parametrize(("firmware", "expected"), [("V4.00", "V4.00"), (None, None)])
async def test_firmware_as_sw_version(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
    device_registry: dr.DeviceRegistry,
    firmware: str | None,
    expected: str | None,
) -> None:
    if firmware is None:
        mock_client.async_get_firmware.side_effect = OekofenError("x")
    else:
        mock_client.async_get_firmware.return_value = firmware
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    main = device_registry.async_get_device_by_identifier(
        (DOMAIN, mock_config_entry.entry_id), mock_config_entry.entry_id
    )
    assert main is not None
    assert main.sw_version == expected


async def test_model_follows_metadata(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
    device_registry: dr.DeviceRegistry,
) -> None:
    data = load_data()
    data.sections["pe1"]["L_type"] = 6  # CONDENS in the enum text
    mock_client.async_get_data.return_value = data
    await tick(hass, freezer, 24 * 3600 + 1)
    main = device_registry.async_get_device_by_identifier(
        (DOMAIN, init_integration.entry_id), init_integration.entry_id
    )
    assert main is not None
    assert main.model == "CONDENS"


async def test_counter_never_decreases(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    first = float(hass.states.get(STARTS).state)
    data = load_data()
    data.sections["pe1"]["L_starts"] = 3
    mock_client.async_get_data.return_value = data
    await tick(hass, freezer, 61)
    assert float(hass.states.get(STARTS).state) == first
    data = load_data()
    data.sections["pe1"]["L_starts"] = int(first) + 5
    mock_client.async_get_data.return_value = data
    await tick(hass, freezer, 61)
    assert float(hass.states.get(STARTS).state) == first + 5


async def test_unexpected_unit_skips_entity(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    data = load_data()
    data.meta["pe1"]["L_avg_runtime"] = FieldMeta(unit="s")
    data.meta["pe1"]["L_runtime"] = FieldMeta(unit="Std")  # unknown unit
    mock_client.async_get_data.return_value = data
    mock_config_entry.add_to_hass(hass)
    with patch("custom_components.oekofen.entity.LOGGER") as logger:
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    assert hass.states.get("sensor.okofen_pellematic_average_burner_runtime") is None
    assert hass.states.get("sensor.okofen_pellematic_burner_hours") is None
    reported = {call.args[3] for call in logger.warning.call_args_list}
    assert reported == {"s", "Std"}


async def test_statistics_survive_restart(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
    hass_storage: dict,
) -> None:
    coordinator = init_integration.runtime_data.coordinator
    data = load_data()
    data.sections["pe1"]["L_state"] = 4  # full burn
    data.sections["pe1"]["L_modulation"] = 100
    mock_client.async_get_data.return_value = data
    await tick(hass, freezer, 60)
    await tick(hass, freezer, 60)
    heat = coordinator.tracker.heat_kwh
    assert heat == pytest.approx(12 / 60)  # one minute at 12 kW
    assert float(hass.states.get("sensor.okofen_pellematic_heat_estimated").state) == (
        pytest.approx(heat, abs=0.001)
    )

    await tick(hass, freezer, 61)  # delayed save
    await hass.config_entries.async_reload(init_integration.entry_id)
    await hass.async_block_till_done()
    restored = init_integration.runtime_data.coordinator.tracker
    assert restored.heat_kwh >= heat

    await hass.config_entries.async_remove(init_integration.entry_id)
    await hass.async_block_till_done()
    assert f"oekofen.{init_integration.entry_id}" not in hass_storage
