"""Diagnostics for ÖkoFEN Pellematic.

The download may be attached to a public issue, so connection data and every
free text of the boiler (circuit names, weather source, fault dates) are
redacted. The location of the weather source is never read in the first place.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .coordinator import OekofenConfigEntry

TO_REDACT_ENTRY = {CONF_HOST, CONF_PASSWORD}
# Free texts set by the owner or derived from the location.
TO_REDACT_VALUES = {"name", "L_source", "L_location"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: OekofenConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT_ENTRY),
            "options": dict(entry.options),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval_s": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
            "has_metadata": coordinator.client.has_metadata,
        },
        "sections": {
            section: async_redact_data(values, TO_REDACT_VALUES)
            for section, values in data.sections.items()
        },
        "metadata": {
            section: {key: asdict(meta) for key, meta in fields.items()}
            for section, fields in data.meta.items()
        },
        "faults": [{"text": f.text, "code": f.code} for f in data.faults],
    }
