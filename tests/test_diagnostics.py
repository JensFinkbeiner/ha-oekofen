"""Tests for the diagnostics download."""

from __future__ import annotations

import json

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator
from syrupy.assertion import SnapshotAssertion

from .conftest import TEST_HOST, TEST_PASSWORD


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    result = await get_diagnostics_for_config_entry(hass, hass_client, init_integration)
    text = json.dumps(result, ensure_ascii=False)

    assert TEST_PASSWORD not in text
    assert TEST_HOST not in text
    assert "Testname" not in text  # circuit names are redacted
    assert "Testwetter" not in text
    assert "Musterstadt" not in text  # location is never read
    assert result == snapshot
