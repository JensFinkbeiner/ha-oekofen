"""The ÖkoFEN Pellematic integration.

Milestone 0.1.0: skeleton only. The config entry loads, but no platforms are
set up yet. The protocol client follows in 0.2.0, entities in 0.3.0.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = []


@dataclass
class OekofenRuntimeData:
    """Runtime objects of one config entry (coordinator follows in 0.3.0)."""


type OekofenConfigEntry = ConfigEntry[OekofenRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: OekofenConfigEntry) -> bool:
    """Set up ÖkoFEN Pellematic from a config entry."""
    entry.runtime_data = OekofenRuntimeData()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OekofenConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
