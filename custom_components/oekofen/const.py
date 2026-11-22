"""Constants for the ÖkoFEN Pellematic integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "oekofen"

DEFAULT_PORT: Final = 4321

# The boiler rejects requests closer than 2.5 s apart, shared by all clients
# (e.g. the Pellet-Monitor). 60 s keeps us far away from that limit.
DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=60)
MIN_SCAN_INTERVAL: Final = timedelta(seconds=30)
