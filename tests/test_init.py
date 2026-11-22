"""Tests for setup, unload, coordinator errors and devices."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.oekofen import async_remove_config_entry_device
from custom_components.oekofen.api import (
    OekofenAuthError,
    OekofenConnectionError,
)
from custom_components.oekofen.api.models import OekofenData
from custom_components.oekofen.const import DOMAIN

from .conftest import load_data

ENTITY = "sensor.okofen_pellematic_boiler_temperature"


async def test_setup_and_unload(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    assert init_integration.state is ConfigEntryState.LOADED
    assert await hass.config_entries.async_unload(init_integration.entry_id)
    await hass.async_block_till_done()
    assert init_integration.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize(
    ("side_effect", "state"),
    [
        (OekofenConnectionError("x"), ConfigEntryState.SETUP_RETRY),
        (OekofenAuthError("x"), ConfigEntryState.SETUP_ERROR),
    ],
)
async def test_setup_fails(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
    side_effect: Exception,
    state: ConfigEntryState,
) -> None:
    mock_client.async_get_data.side_effect = side_effect
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is state


async def test_unavailable_and_back(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    assert hass.states.get(ENTITY).state != STATE_UNAVAILABLE

    mock_client.async_get_data.side_effect = OekofenConnectionError("x")
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).state == STATE_UNAVAILABLE

    mock_client.async_get_data.side_effect = None
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).state != STATE_UNAVAILABLE


async def test_auth_error_starts_reauth(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    mock_client.async_get_data.side_effect = OekofenAuthError("x")
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress()
    assert any(f["context"]["source"] == SOURCE_REAUTH for f in flows)


async def test_metadata_refreshed_daily(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    calls = mock_client.async_get_data.await_args_list
    assert calls[0].kwargs == {"refresh_metadata": True}
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert calls[-1].kwargs == {"refresh_metadata": False}
    freezer.tick(timedelta(hours=24))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert calls[-1].kwargs == {"refresh_metadata": True}


async def test_devices(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    main = device_registry.async_get_device_by_identifier(
        (DOMAIN, init_integration.entry_id), init_integration.entry_id
    )
    assert main is not None
    assert main.manufacturer == "ÖkoFEN"
    assert main.model == "COMPACT"
    for section in ("hk1", "pu1", "ww1", "circ1"):
        child = device_registry.async_get_child_device_by_identifier(
            (DOMAIN, f"{init_integration.entry_id}_{section}"),
            init_integration.entry_id,
        )
        assert child is not None, section
        assert child.parent_device_id == main.id


async def test_new_section_adds_entities_and_stale_device_removal(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_client: MagicMock,
    device_registry: dr.DeviceRegistry,
    freezer: FrozenDateTimeFactory,
) -> None:
    data = load_data()
    data.sections["hk2"] = dict(data.sections["hk1"])
    mock_client.async_get_data.return_value = data
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert (
        hass.states.get("sensor.okofen_pellematic_heating_circuit_2_flow_temperature")
        is not None
    )

    hk2 = device_registry.async_get_child_device_by_identifier(
        (DOMAIN, f"{init_integration.entry_id}_hk2"), init_integration.entry_id
    )
    main = device_registry.async_get_device_by_identifier(
        (DOMAIN, init_integration.entry_id), init_integration.entry_id
    )
    assert hk2 is not None
    assert main is not None

    # hk2 still present: cannot be removed; main device never
    assert not await async_remove_config_entry_device(hass, init_integration, hk2)
    assert not await async_remove_config_entry_device(hass, init_integration, main)

    mock_client.async_get_data.return_value = load_data()
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(
        "sensor.okofen_pellematic_heating_circuit_2_flow_temperature"
    ).state == (STATE_UNAVAILABLE)
    assert await async_remove_config_entry_device(hass, init_integration, hk2)


async def test_missing_model_without_metadata(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
    device_registry: dr.DeviceRegistry,
) -> None:
    data = load_data()
    mock_client.async_get_data.return_value = OekofenData(sections=data.sections)
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    main = device_registry.async_get_device_by_identifier(
        (DOMAIN, mock_config_entry.entry_id), mock_config_entry.entry_id
    )
    assert main is not None
    assert main.model is None


async def test_device_removal_refused_when_not_loaded(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    hk1 = device_registry.async_get_child_device_by_identifier(
        (DOMAIN, f"{init_integration.entry_id}_hk1"), init_integration.entry_id
    )
    assert hk1 is not None
    await hass.config_entries.async_unload(init_integration.entry_id)
    await hass.async_block_till_done()
    assert not await async_remove_config_entry_device(hass, init_integration, hk1)
