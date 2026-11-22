"""Tests for the binary sensors."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from .conftest import load_data

BURNER = "binary_sensor.okofen_pellematic_burner"
HK_PUMP = "binary_sensor.okofen_pellematic_heating_circuit_1_pump"


@pytest.fixture
def platforms() -> list[Platform]:
    return [Platform.BINARY_SENSOR]


async def test_binary_sensors(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    await snapshot_platform(hass, entity_registry, snapshot, init_integration.entry_id)


@pytest.mark.parametrize(
    ("entity_id", "section", "key", "value", "expected"),
    [
        (BURNER, "pe1", "L_state", 4, STATE_ON),
        (BURNER, "pe1", "L_state", 5, STATE_OFF),
        (BURNER, "pe1", "L_state", None, STATE_UNKNOWN),
        (HK_PUMP, "hk1", "L_pump", 1, STATE_ON),
        (HK_PUMP, "hk1", "L_pump", 0, STATE_OFF),
        (HK_PUMP, "hk1", "L_pump", True, STATE_ON),
        (HK_PUMP, "hk1", "L_pump", "x", STATE_UNKNOWN),
    ],
)
async def test_states(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
    entity_id: str,
    section: str,
    key: str,
    value: object,
    expected: str,
) -> None:
    data = load_data()
    data.sections[section][key] = value  # type: ignore[assignment]
    mock_client.async_get_data.return_value = data
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == expected
