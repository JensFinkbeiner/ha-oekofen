"""Compare the burner statistics of the integration with the Pellet-Monitor.

Usage (from the repository root, Python 3.14 in the tools container):
    docker compose -f devenv/compose.yaml run --rm tools uv run python tools/compare_monitor.py

    MONITOR_DB  copy of the Pellet-Monitor database, default local/pellet-monitor.sqlite3
    HA_DB       recorder database of Home Assistant, default devenv/config/home-assistant_v2.db

Per complete local day (both sources recorded the whole day) it prints:
burner starts, burner runtime in minutes and heat in kWh from both sources, the
deviation and PASS/FAIL against the tolerances of PLAN.md (starts equal,
runtime ±2 %, heat ±5 %). Only these numbers are printed, no raw values.
Nominal power for the monitor side: 12 kW (or --kw).
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta
from itertools import pairwise
import json
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
TZ = ZoneInfo("Europe/Berlin")
MAX_STEP_S = 300
ENTITY_KEYS = {
    "starts": "pe1_starts_today",
    "runtime": "pe1_runtime_today",
    "heat": "pe1_heat_energy",
}
TOLERANCE = {"starts": 0.0, "runtime": 0.02, "heat": 0.05}


def local_day(ts: float) -> date:
    return datetime.fromtimestamp(ts, TZ).date()


def day_bounds(day: date) -> tuple[float, float]:
    start = datetime(day.year, day.month, day.day, tzinfo=TZ)
    return start.timestamp(), (start + timedelta(days=1)).timestamp()


def monitor_days(db: Path, kw: float) -> dict[date, dict[str, float]]:
    """Starts (counter), runtime and heat per day from the Pellet-Monitor."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT ts, pe1_starts, pe1_burning, pe1_modulation FROM measurements ORDER BY ts"
    ).fetchall()
    con.close()
    days: dict[date, dict[str, float]] = defaultdict(
        lambda: {"starts": 0.0, "runtime": 0.0, "heat": 0.0, "first": 0.0, "last": 0.0}
    )
    last_counter: dict[date, int] = {}
    for i, (ts, starts, burning, modulation) in enumerate(rows):
        day = local_day(ts)
        d = days[day]
        d["first"] = d["first"] or ts
        d["last"] = ts
        if starts is not None:
            last_counter[day] = starts
        nxt = rows[i + 1][0] if i + 1 < len(rows) else ts
        dt = min(nxt - ts, MAX_STEP_S)
        if burning:
            d["runtime"] += dt / 60
            d["heat"] += kw * (modulation or 0) / 100 * dt / 3600
    ordered = sorted(last_counter)
    for prev, cur in pairwise(ordered):
        days[cur]["starts"] = last_counter[cur] - last_counter[prev]
    return days


def ha_entities(ha_db: Path) -> dict[str, str]:
    registry = ha_db.parent / ".storage" / "core.entity_registry"
    entities = json.loads(registry.read_text(encoding="utf-8"))["data"]["entities"]
    found = {}
    for name, suffix in ENTITY_KEYS.items():
        for e in entities:
            if e["platform"] == "oekofen" and e["unique_id"].endswith(suffix):
                found[name] = e["entity_id"]
    return found


def ha_days(ha_db: Path) -> dict[date, dict[str, float]]:
    """Last value of the day (daily counters) and daily delta of the heat total."""
    entities = ha_entities(ha_db)
    con = sqlite3.connect(f"file:{ha_db}?mode=ro", uri=True)
    days: dict[date, dict[str, float]] = defaultdict(dict)
    heat_by_day: dict[date, list[float]] = defaultdict(list)
    first_last: dict[date, list[float]] = defaultdict(list)
    for name, entity_id in entities.items():
        rows = con.execute(
            "SELECT s.last_updated_ts, s.state FROM states s"
            " JOIN states_meta m ON s.metadata_id = m.metadata_id"
            " WHERE m.entity_id = ? ORDER BY s.last_updated_ts",
            (entity_id,),
        ).fetchall()
        for ts, state in rows:
            try:
                value = float(state)
            except TypeError, ValueError:
                continue
            day = local_day(ts)
            first_last[day].append(ts)
            if name == "heat":
                heat_by_day[day].append(value)
            else:
                days[day][name] = value  # rows are ordered: keeps the last
    con.close()
    for day, values in heat_by_day.items():
        days[day]["heat"] = max(values) - min(values)
    for day, stamps in first_last.items():
        days[day]["first"], days[day]["last"] = min(stamps), max(stamps)
    return days


def complete(day: date, d: dict[str, float]) -> bool:
    start, end = day_bounds(day)
    return d.get("first", end) - start < 600 and end - d.get("last", start) < 600


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "monitor_db", nargs="?", default=ROOT / "local" / "pellet-monitor.sqlite3"
    )
    parser.add_argument(
        "ha_db", nargs="?", default=ROOT / "devenv" / "config" / "home-assistant_v2.db"
    )
    parser.add_argument("--kw", type=float, default=12.0)
    args = parser.parse_args()

    mon = monitor_days(Path(args.monitor_db), args.kw)
    ha = ha_days(Path(args.ha_db))
    shared = sorted(
        d for d in ha if d in mon and complete(d, ha[d]) and complete(d, mon[d])
    )
    if not shared:
        print("No complete day recorded by both sources yet.")
        return
    print(f"{'day':10}  {'value':8} {'HA':>9} {'monitor':>9} {'dev':>7}  result")
    failed = 0
    for day in shared:
        for name in ("starts", "runtime", "heat"):
            a, b = ha[day].get(name), mon[day][name]
            if a is None:
                print(f"{day}  {name:8} {'-':>9} {b:9.2f} {'-':>7}  MISSING")
                failed += 1
                continue
            dev = 0.0 if b == 0 and a == 0 else abs(a - b) / max(abs(b), 1e-9)
            ok = (a == b) if name == "starts" else dev <= TOLERANCE[name]
            failed += not ok
            print(
                f"{day}  {name:8} {a:9.2f} {b:9.2f} {dev:7.1%}  {'PASS' if ok else 'FAIL'}"
            )
    print(f"\n{len(shared)} day(s) compared, {failed} value(s) outside the tolerance.")


if __name__ == "__main__":
    main()
