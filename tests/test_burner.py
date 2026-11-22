"""Tests for the burner statistics with invented sequences (no Home Assistant)."""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.oekofen.burner import (
    MAX_STEP_S,
    SHORT_RUN_S,
    BurnerTracker,
    EnergyModel,
    Sample,
)

DAY = date(2026, 11, 22)
NEXT = date(2026, 11, 23)
MODEL = EnergyModel(nominal_kw=12, efficiency=0.9, heating_value_kwh_per_kg=5)


def feed(
    tracker: BurnerTracker,
    states: list[tuple[float, bool, float, int]],
    day: date = DAY,
    model: EnergyModel = MODEL,
) -> None:
    for ts, burning, modulation, starts in states:
        tracker.update(Sample(ts, day, burning, modulation, starts), model)


def test_one_run_energy_and_duration() -> None:
    tracker = BurnerTracker()
    # off, then burning at 50 % for 30 polls of 60 s, then off
    states = [(0, False, 0, 100)]
    states += [(60 * i, True, 50, 101) for i in range(1, 31)]
    states += [(60 * 31, False, 0, 101)]
    feed(tracker, states)

    assert tracker.starts_today == 1
    assert tracker.runtime_today_s == 30 * 60
    # run from midpoint 30 s to midpoint 1830 s
    assert tracker.last_run_s == 1800
    assert tracker.short_runs_today == 0
    # 12 kW x 50 % x 0.5 h = 3 kWh heat; 3 / (0.9 x 5) = 0.667 kg
    assert tracker.heat_kwh == pytest.approx(3.0)
    assert tracker.pellets_kg == pytest.approx(3.0 / 4.5)
    assert tracker.runtime_today_min == 30
    assert tracker.last_run_min == 30


def test_short_run_counted() -> None:
    tracker = BurnerTracker()
    feed(
        tracker,
        [(0, False, 0, 5), (60, True, 100, 6), (120, True, 100, 6), (180, False, 0, 6)],
    )
    assert tracker.last_run_s == 120
    assert tracker.last_run_s < SHORT_RUN_S
    assert tracker.short_runs_today == 1


def test_gap_discards_open_run_and_does_not_fill() -> None:
    tracker = BurnerTracker()
    feed(tracker, [(0, False, 0, 5), (60, True, 100, 6)])
    # HA was down for an hour, burner is off again
    feed(
        tracker,
        [(60 + MAX_STEP_S + 3600, False, 0, 7), (60 + MAX_STEP_S + 3660, False, 0, 7)],
    )
    assert tracker.last_run_s is None
    assert tracker.runtime_today_s == 0
    assert tracker.heat_kwh == 0
    # the start during the gap is still counted from the boiler counter
    assert tracker.starts_today == 2


def test_new_day_resets_daily_values_not_totals() -> None:
    tracker = BurnerTracker()
    feed(tracker, [(0, True, 100, 10), (60, True, 100, 10), (120, False, 0, 10)])
    heat = tracker.heat_kwh
    assert tracker.runtime_today_s == 120
    feed(tracker, [(180, False, 0, 10), (240, True, 100, 11)], day=NEXT)
    assert tracker.starts_today == 1
    assert tracker.runtime_today_s == 0
    assert tracker.short_runs_today == 0
    assert tracker.heat_kwh == heat


def test_counter_reset_and_missing_values() -> None:
    tracker = BurnerTracker()
    tracker.update(Sample(0, DAY, None, None, None), MODEL)
    assert tracker.starts_today is None
    feed(tracker, [(60, True, 120, 50), (120, True, 50, 52)])
    assert tracker.starts_today == 2
    # modulation above 100 % is capped: 12 kW x 1/60 h
    assert tracker.heat_kwh == pytest.approx(0.2)
    feed(tracker, [(180, False, 0, 3)])  # board replaced: counter starts again
    assert tracker.starts_today == 0
    tracker.update(Sample(240, DAY, False, None, None), MODEL)
    assert tracker.starts_today == 0


def test_burning_without_modulation_counts_time_but_no_energy() -> None:
    tracker = BurnerTracker()
    tracker.update(Sample(0, DAY, True, None, 1), MODEL)
    tracker.update(Sample(60, DAY, True, None, 1), MODEL)
    assert tracker.runtime_today_s == 60
    assert tracker.heat_kwh == 0


def test_day_start_without_counter_uses_last_counter() -> None:
    tracker = BurnerTracker()
    feed(tracker, [(0, False, 0, 40)])
    tracker.update(Sample(60, NEXT, False, 0, None), MODEL)
    assert tracker.starts_at_day_start == 40
    assert tracker.starts_today == 0


def test_calibration_changes_pellets() -> None:
    model = EnergyModel(
        nominal_kw=12, efficiency=0.9, heating_value_kwh_per_kg=5, calibration=1.2
    )
    tracker = BurnerTracker()
    feed(tracker, [(0, True, 100, 1), (3600 - 1, True, 100, 1)], model=model)
    assert tracker.pellets_kg == pytest.approx(0)  # gap > MAX_STEP_S
    tracker = BurnerTracker()
    feed(tracker, [(0, True, 100, 1), (300, True, 100, 1)], model=model)
    assert tracker.pellets_kg == pytest.approx(1.0 * 1.2 / 4.5)


def test_roundtrip_and_broken_store() -> None:
    tracker = BurnerTracker()
    feed(tracker, [(0, False, 0, 9), (60, True, 80, 10), (120, False, 0, 10)])
    restored = BurnerTracker.from_dict(tracker.as_dict())
    assert restored == tracker
    assert restored.as_dict() == tracker.as_dict()
    assert BurnerTracker.from_dict(None) == BurnerTracker()
    assert BurnerTracker.from_dict({"unknown": 1}) == BurnerTracker()
