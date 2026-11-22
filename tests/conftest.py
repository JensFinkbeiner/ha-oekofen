"""Shared fixtures. All test data is invented."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.oekofen.const import DOMAIN

# RFC 5737 documentation address, never a real device.
TEST_HOST = "192.0.2.10"
TEST_PORT = 4321
TEST_PASSWORD = "testpw"


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
        title="ÖkoFEN Pellematic",
        data={CONF_HOST: TEST_HOST, CONF_PORT: TEST_PORT, CONF_PASSWORD: TEST_PASSWORD},
    )
