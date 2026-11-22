"""Connection data for the local helper scripts.

Read from the oekofen config entry of the HA test instance (devenv/config, never
committed) so that nobody has to type or print the password. Never print the
returned values.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRIES = ROOT / "devenv" / "config" / ".storage" / "core.config_entries"
RAW_DIR = ROOT / "local" / "raw"


def connection() -> tuple[str, int, str]:
    """Return host, port and password of the first oekofen config entry."""
    data = json.loads(ENTRIES.read_text(encoding="utf-8"))
    for entry in data["data"]["entries"]:
        if entry["domain"] == "oekofen":
            d = entry["data"]
            return str(d["host"]), int(d["port"]), str(d["password"])
    raise SystemExit("No oekofen config entry found in the HA test instance.")


def mask(text: str, password: str, host: str) -> str:
    """Remove password and host from a message before printing it."""
    return text.replace(password, "***").replace(host, "<host>")
