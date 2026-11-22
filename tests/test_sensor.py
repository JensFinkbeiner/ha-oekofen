"""Tests for the sensors (snapshots of all entities)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNKNOWN, Platform
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


@pytest.fixture
def platforms() -> list[Platform]:
    return [Platform.SENSOR]


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    await snapshot_platform(hass, entity_registry, snapshot, init_integration.entry_id)


async def test_disabled_by_default(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    entry = entity_registry.async_get(
        "sensor.okofen_pellematic_heating_circuit_1_room_temperature"
    )
    assert entry is not None
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    ("section", "key", "value", "entity_id", "expected"),
    [
        ("pe1", "L_state", 42, "sensor.okofen_pellematic_burner_phase", STATE_UNKNOWN),
        ("pe1", "L_state", "x", "sensor.okofen_pellematic_burner_phase", STATE_UNKNOWN),
        ("pe1", "L_state", 4, "sensor.okofen_pellematic_burner_phase", "full_burn"),
        ("pe1", "L_statetext", " ", "sensor.okofen_pellematic_status", STATE_UNKNOWN),
        (
            "hk1",
            "L_statetext",
            "Absenkbetrieb aktiv|Heizgrenze",
            "sensor.okofen_pellematic_heating_circuit_1_status",
            "Absenkbetrieb aktiv, Heizgrenze",
        ),
        (
            "pe1",
            "L_temp_act",
            None,
            "sensor.okofen_pellematic_boiler_temperature",
            STATE_UNKNOWN,
        ),
        (
            "pe1",
            "L_modulation",
            150,
            "sensor.okofen_pellematic_modulation",
            STATE_UNKNOWN,
        ),
        ("pe1", "L_modulation", 80, "sensor.okofen_pellematic_modulation", "80"),
        (
            "hk1",
            "L_roomtemp_act",
            0,
            "sensor.okofen_pellematic_heating_circuit_1_room_temperature",
            STATE_UNKNOWN,
        ),
        (
            "pe1",
            "L_temp_act",
            True,
            "sensor.okofen_pellematic_boiler_temperature",
            STATE_UNKNOWN,
        ),
    ],
)
async def test_value_conversion(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
    section: str,
    key: str,
    value: object,
    entity_id: str,
    expected: str,
) -> None:
    data = load_data()
    data.sections[section][key] = value  # type: ignore[assignment]
    mock_client.async_get_data.return_value = data
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == expected
