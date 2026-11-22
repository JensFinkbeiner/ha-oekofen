"""Shared fixtures. All test data is invented or anonymized."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.oekofen.api import OekofenData
from custom_components.oekofen.api.decode import (
    build_data,
    decode_bytes,
    parse_json,
    parse_meta,
)
from custom_components.oekofen.const import DEFAULT_TITLE, DOMAIN

# RFC 5737 documentation address, never a real device.
TEST_HOST = "192.0.2.10"
TEST_PORT = 4321
TEST_PASSWORD = "testpw"

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_data() -> OekofenData:
    """Return the anonymized real answer (metadata form) as normalized data."""
    raw = parse_json(decode_bytes((FIXTURES / "all_meta.json").read_bytes()))
    return build_data(raw, parse_meta(raw))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Load custom_components/ in every test."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry with invented connection data."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=DEFAULT_TITLE,
        data={CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT, CONF_PASSWORD: TEST_PASSWORD},
        entry_id="01TESTENTRY",
    )


@pytest.fixture
def mock_client() -> Generator[MagicMock]:
    """Patch the protocol client in setup and config flow."""
    with (
        patch("custom_components.oekofen.OekofenClient", autospec=True) as client,
        patch("custom_components.oekofen.config_flow.OekofenClient", new=client),
    ):
        instance = client.return_value
        instance.async_get_data = AsyncMock(return_value=load_data())
        yield instance


@pytest.fixture
def platforms() -> list[Platform]:
    """Platforms to set up (snapshot tests limit this to one)."""
    return [Platform.BINARY_SENSOR, Platform.SENSOR]


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
    platforms: list[Platform],
) -> MockConfigEntry:
    """Set up the integration with the fixture data."""
    mock_config_entry.add_to_hass(hass)
    with patch("custom_components.oekofen.PLATFORMS", platforms):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    return mock_config_entry


@pytest.fixture
def entity_registry_enabled_by_default() -> Generator[None]:
    """Enable all entities, also those disabled by default (as in HA core)."""
    with patch(
        "homeassistant.helpers.entity.Entity.entity_registry_enabled_default",
        return_value=True,
        new_callable=PropertyMock,
    ):
        yield
