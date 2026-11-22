"""The ÖkoFEN Pellematic integration (read-only, local JSON interface)."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OekofenClient, OekofenError
from .const import DOMAIN, LOGGER
from .coordinator import (
    OekofenConfigEntry,
    OekofenCoordinator,
    OekofenRuntimeData,
    fault_issue_id,
)
from .entity import (
    async_register_main_device,
    main_device_identifier,
    section_device_identifier,
)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: OekofenConfigEntry) -> bool:
    """Set up ÖkoFEN Pellematic from a config entry."""
    client = OekofenClient(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_PASSWORD],
        async_get_clientsession(hass),
    )
    coordinator = OekofenCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    try:
        firmware = await client.async_get_firmware()
    except OekofenError:
        firmware = None  # only cosmetic, never block the setup
        LOGGER.debug("Firmware version not available")
    entry.runtime_data = OekofenRuntimeData(
        client=client,
        coordinator=coordinator,
        main_device_id=async_register_main_device(
            hass, entry, coordinator.data, firmware
        ),
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OekofenConfigEntry) -> bool:
    """Unload a config entry."""
    ir.async_delete_issue(hass, DOMAIN, fault_issue_id(entry))
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: OekofenConfigEntry, device_entry: dr.AnyDeviceEntry
) -> bool:
    """Allow removing a child device whose section the boiler no longer sends."""
    if main_device_identifier(entry) in device_entry.identifiers:
        return False
    if entry.state is not ConfigEntryState.LOADED:
        return False
    present = {
        section_device_identifier(entry, section)
        for section in entry.runtime_data.coordinator.data.sections
    }
    return not present & device_entry.identifiers
