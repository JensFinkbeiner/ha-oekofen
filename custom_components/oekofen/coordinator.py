"""Data update coordinator for ÖkoFEN Pellematic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import OekofenAuthError, OekofenClient, OekofenData, OekofenError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER, METADATA_REFRESH


@dataclass
class OekofenRuntimeData:
    """Runtime objects of one config entry."""

    client: OekofenClient
    coordinator: OekofenCoordinator
    main_device_id: str


type OekofenConfigEntry = ConfigEntry[OekofenRuntimeData]


class OekofenCoordinator(DataUpdateCoordinator[OekofenData]):
    """Poll the boiler in one request per interval."""

    config_entry: OekofenConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: OekofenConfigEntry, client: OekofenClient
    ) -> None:
        """Initialize the coordinator."""
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.client = client
        self._metadata_loaded_at = dt_util.utcnow() - METADATA_REFRESH

    async def _async_update_data(self) -> OekofenData:
        """Fetch the data; reload the field descriptions once a day."""
        now = dt_util.utcnow()
        refresh = now - self._metadata_loaded_at >= METADATA_REFRESH
        try:
            data = await self.client.async_get_data(refresh_metadata=refresh)
        except OekofenAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="invalid_auth"
            ) from err
        except OekofenError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        if refresh:
            self._metadata_loaded_at = now
        return data
