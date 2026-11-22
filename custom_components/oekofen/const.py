"""Constants for the ÖkoFEN Pellematic integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Final

DOMAIN: Final = "oekofen"
LOGGER = logging.getLogger(__package__)

MANUFACTURER: Final = "ÖkoFEN"
DEFAULT_TITLE: Final = "ÖkoFEN Pellematic"
DEFAULT_PORT: Final = 4321

# The boiler rejects requests closer than 2.5 s apart, shared by all clients
# (e.g. the Pellet-Monitor). 60 s keeps us far away from that limit.
DEFAULT_SCAN_INTERVAL: Final = 60
MIN_SCAN_INTERVAL: Final = 30
MAX_SCAN_INTERVAL: Final = 3600
# Longest interval while the boiler stays unreachable (doubling backoff).
MAX_BACKOFF: Final = timedelta(minutes=10)

# Factors, units and enum texts rarely change; reload them once a day.
METADATA_REFRESH: Final = timedelta(hours=24)

# Boiler phases (pe.L_state) in which pellets are fed and burnt. Not 5 (burn-out).
# pe.L_br does not show the burner on the Pellematic Compact
# (checked by the Pellet-Monitor, 15.10.2026).
BURNING_STATES: Final = frozenset({0, 1, 2, 3, 4})

# pe.L_state -> translation key of the enum sensor "burner phase".
BURNER_PHASES: Final[dict[int, str]] = {
    0: "continuous_run",
    1: "start",
    2: "ignition",
    3: "soft_start",
    4: "full_burn",
    5: "burn_out",
    6: "off",
    7: "suction",
    8: "ash_warning",
    9: "pellet_warning",
    10: "pellet_switch",
    11: "fault",
    12: "calibration",
    97: "off",
    98: "off",
    99: "off",
    100: "off",
    101: "off",
}
