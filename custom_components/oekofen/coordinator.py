"""Data update coordinator for ÖkoFEN Pellematic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr, issue_registry as ir
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    OekofenAuthError,
    OekofenBusyError,
    OekofenClient,
    OekofenData,
    OekofenError,
)
from .burner import STORE_VERSION, BurnerTracker, EnergyModel, Sample
from .const import (
    BURNING_STATES,
    CONF_CALIBRATION,
    CONF_EFFICIENCY,
    CONF_HEATING_VALUE,
    CONF_NOMINAL_KW,
    DEFAULT_CALIBRATION,
    DEFAULT_EFFICIENCY,
    DEFAULT_HEATING_VALUE,
    DEFAULT_NOMINAL_KW,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_BACKOFF,
    METADATA_REFRESH,
)


@dataclass
class OekofenRuntimeData:
    """Runtime objects of one config entry."""

    client: OekofenClient
    coordinator: OekofenCoordinator
    main_device_id: str


type OekofenConfigEntry = ConfigEntry[OekofenRuntimeData]


def fault_issue_id(entry: OekofenConfigEntry) -> str:
    """Return the id of the repair issue for a boiler fault."""
    return f"boiler_fault_{entry.entry_id}"


STORE_SAVE_DELAY = 60


def energy_model(options: dict[str, float]) -> EnergyModel:
    """Return the energy estimate settings from the options of an entry."""
    return EnergyModel(
        nominal_kw=float(options.get(CONF_NOMINAL_KW, DEFAULT_NOMINAL_KW)),
        efficiency=float(options.get(CONF_EFFICIENCY, DEFAULT_EFFICIENCY)) / 100,
        heating_value_kwh_per_kg=float(
            options.get(CONF_HEATING_VALUE, DEFAULT_HEATING_VALUE)
        ),
        calibration=float(options.get(CONF_CALIBRATION, DEFAULT_CALIBRATION)),
    )


def _sample(data: OekofenData, ts: float) -> Sample:
    state = data.get("pe1", "L_state")
    modulation = data.get("pe1", "L_modulation")
    starts = data.get("pe1", "L_starts")
    is_int = isinstance(state, int) and not isinstance(state, bool)
    return Sample(
        ts=ts,
        day=dt_util.as_local(dt_util.utc_from_timestamp(ts)).date(),
        burning=(state in BURNING_STATES) if is_int else None,
        modulation=float(modulation)
        if isinstance(modulation, int | float) and not isinstance(modulation, bool)
        else None,
        starts=starts
        if isinstance(starts, int) and not isinstance(starts, bool)
        else None,
    )


def boiler_model(data: OekofenData) -> str | None:
    """Return the boiler type from its enum text, e.g. "COMPACT"."""
    value = data.get("pe1", "L_type")
    meta = data.field_meta("pe1", "L_type")
    if isinstance(value, int) and meta and meta.options:
        return meta.options.get(value)
    return None


class OekofenCoordinator(DataUpdateCoordinator[OekofenData]):
    """Poll the boiler in one request per interval."""

    config_entry: OekofenConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: OekofenConfigEntry, client: OekofenClient
    ) -> None:
        """Initialize the coordinator."""
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        self._base_interval = timedelta(seconds=interval)
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=self._base_interval,
        )
        self.client = client
        self._metadata_loaded_at = dt_util.utcnow() - METADATA_REFRESH
        self._failures = 0
        self._busy_skipped = False
        self.energy_model = energy_model(dict(entry.options))
        self.tracker = BurnerTracker()
        self._store: Store[dict[str, object]] = Store(
            hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )

    async def async_load_statistics(self) -> None:
        """Restore the burner statistics saved before the last restart."""
        self.tracker = BurnerTracker.from_dict(await self._store.async_load())

    async def async_save_statistics(self) -> None:
        """Write the statistics now (unload/reload; HA flushes on shutdown)."""
        await self._store.async_save(self.tracker.as_dict())

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
        except OekofenBusyError as err:
            # Collision with another client (e.g. the Pellet-Monitor) even after
            # the retry: keep the last values once instead of going unavailable.
            if self.data is not None and not self._busy_skipped:
                self._busy_skipped = True
                LOGGER.debug("Boiler busy, keeping the previous values once")
                return self.data
            self._on_failure()
            raise self._update_failed(err) from err
        except OekofenError as err:
            self._on_failure()
            raise self._update_failed(err) from err
        self._busy_skipped = False
        if self._failures:
            self._failures = 0
            self.update_interval = self._base_interval
        if refresh:
            self._metadata_loaded_at = now
            self._async_update_model(data)
        self._async_update_fault_issue(data)
        self.tracker.update(
            _sample(data, dt_util.utcnow().timestamp()), self.energy_model
        )
        self._store.async_delay_save(self.tracker.as_dict, STORE_SAVE_DELAY)
        return data

    @staticmethod
    def _update_failed(err: OekofenError) -> UpdateFailed:
        return UpdateFailed(
            translation_domain=DOMAIN,
            translation_key="update_failed",
            translation_placeholders={"error": str(err)},
        )

    def _on_failure(self) -> None:
        """Back off while the boiler stays unreachable (doubling, max 10 min)."""
        self._failures += 1
        backoff = self._base_interval * 2 ** min(self._failures - 1, 6)
        self.update_interval = min(backoff, max(MAX_BACKOFF, self._base_interval))

    def _async_update_model(self, data: OekofenData) -> None:
        """Keep the model of the main device in sync with the metadata."""
        runtime = getattr(self.config_entry, "runtime_data", None)
        model = boiler_model(data)
        if runtime is None or model is None:
            return
        registry = dr.async_get(self.hass)
        device = registry.async_get(runtime.main_device_id)
        if device is not None and getattr(device, "model", None) != model:
            registry.async_update_device(runtime.main_device_id, model=model)

    def _async_update_fault_issue(self, data: OekofenData) -> None:
        """Show a repair issue while the boiler reports a fault."""
        issue_id = fault_issue_id(self.config_entry)
        if not data.faults:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            return
        fault = data.faults[0]
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key="boiler_fault",
            translation_placeholders={
                "fault": fault.text,
                "code": str(fault.code) if fault.code is not None else "-",
                "count": str(len(data.faults)),
            },
        )
