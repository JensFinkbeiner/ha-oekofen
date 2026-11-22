"""Burner statistics and estimated energy, computed from consecutive polls.

Pure logic without Home Assistant, so it can be tested with invented sequences.
Same model as the Pellet-Monitor:

- Each poll stands for the time until the next one, at most MAX_STEP_S
  (longer gaps are not filled).
- Burner load hours = sum of modulation x time while burning.
- Heat [kWh] = load hours x nominal power.
- Pellets [kg] = heat / (efficiency x heating value) x calibration.
- A run starts or ends halfway between the two polls that show the change.
- Starts per day come from the boiler counter (pe.L_starts), so starts during
  a gap are still counted.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

MAX_STEP_S = 300
SHORT_RUN_S = 15 * 60  # shorter runs count as cycling ("Kurzlauf")
STORE_VERSION = 1


@dataclass(frozen=True, slots=True)
class EnergyModel:
    """Settings of the estimate (from the options of the config entry)."""

    nominal_kw: float = 12.0
    efficiency: float = 0.91
    heating_value_kwh_per_kg: float = 4.8
    calibration: float = 1.0

    @property
    def kg_per_kwh_heat(self) -> float:
        """Pellets needed for one kWh of heat."""
        return self.calibration / (self.efficiency * self.heating_value_kwh_per_kg)


@dataclass(frozen=True, slots=True)
class Sample:
    """One poll of the boiler, reduced to what the statistics need."""

    ts: float
    day: date
    burning: bool | None
    modulation: float | None
    starts: int | None


@dataclass
class BurnerTracker:
    """Accumulate runs, daily values and energy over consecutive samples."""

    last_ts: float | None = None
    last_burning: bool | None = None
    last_modulation: float | None = None
    run_start_ts: float | None = None
    day: str | None = None
    starts_at_day_start: int | None = None
    starts_today: int | None = None
    runtime_today_s: float = 0.0
    short_runs_today: int = 0
    last_run_s: float | None = None
    heat_kwh: float = 0.0
    pellets_kg: float = 0.0
    _counter: int | None = field(default=None, repr=False)

    def update(self, sample: Sample, model: EnergyModel) -> None:
        """Process the next poll."""
        day = sample.day.isoformat()
        if self.day != day:
            self._new_day(day, sample.starts)

        gap = self.last_ts is None or sample.ts - self.last_ts > MAX_STEP_S
        if not gap and self.last_ts is not None:
            self._accumulate(sample.ts - self.last_ts, model)
            self._detect_run(sample)
        else:
            # Recording gap (HA restart, boiler unreachable): an open run is lost,
            # a run that is on now started at an unknown time.
            self.run_start_ts = None

        self._count_starts(sample.starts)
        self.last_ts = sample.ts
        self.last_burning = sample.burning
        self.last_modulation = sample.modulation

    def _new_day(self, day: str, starts: int | None) -> None:
        self.day = day
        self.starts_at_day_start = starts if starts is not None else self._counter
        self.starts_today = 0 if self.starts_at_day_start is not None else None
        self.runtime_today_s = 0.0
        self.short_runs_today = 0

    def _accumulate(self, dt: float, model: EnergyModel) -> None:
        if not self.last_burning or dt <= 0:
            return
        self.runtime_today_s += dt
        modulation = self.last_modulation if self.last_modulation is not None else 0
        heat = model.nominal_kw * max(0.0, min(modulation, 100.0)) / 100 * dt / 3600
        self.heat_kwh += heat
        self.pellets_kg += heat * model.kg_per_kwh_heat

    def _detect_run(self, sample: Sample) -> None:
        if self.last_ts is None or sample.burning is None or self.last_burning is None:
            return
        midpoint = (self.last_ts + sample.ts) / 2
        if sample.burning and not self.last_burning:
            self.run_start_ts = midpoint
        elif self.last_burning and not sample.burning and self.run_start_ts is not None:
            self.last_run_s = midpoint - self.run_start_ts
            if self.last_run_s < SHORT_RUN_S:
                self.short_runs_today += 1
            self.run_start_ts = None

    def _count_starts(self, starts: int | None) -> None:
        if starts is None:
            return
        if self.starts_at_day_start is None or starts < self.starts_at_day_start:
            # first value of the day, or the counter was reset
            self.starts_at_day_start = starts
        self.starts_today = starts - self.starts_at_day_start
        self._counter = starts

    @property
    def runtime_today_min(self) -> float:
        """Burner runtime today in minutes."""
        return self.runtime_today_s / 60

    @property
    def last_run_min(self) -> float | None:
        """Duration of the last complete run in minutes."""
        return None if self.last_run_s is None else self.last_run_s / 60

    def as_dict(self) -> dict[str, Any]:
        """Return the state for persistent storage."""
        data = asdict(self)
        data["counter"] = data.pop("_counter")
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> BurnerTracker:
        """Restore the state; unknown or broken data gives a fresh tracker."""
        if not isinstance(data, dict):
            return cls()
        values = dict(data)
        counter = values.pop("counter", None)
        try:
            tracker = cls(**values)
        except TypeError:
            return cls()
        tracker._counter = counter
        return tracker
