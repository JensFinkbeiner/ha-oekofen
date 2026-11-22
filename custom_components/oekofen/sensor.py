"""Sensors for ÖkoFEN Pellematic."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfMass,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import BURNER_PHASES
from .coordinator import OekofenConfigEntry, OekofenCoordinator
from .entity import (
    OekofenEntity,
    OekofenEntityDescription,
    async_setup_section_entities,
)

PARALLEL_UPDATES = 0

STATE_TEXT_MAX = 255


@dataclass(frozen=True, kw_only=True)
class OekofenSensorEntityDescription(OekofenEntityDescription, SensorEntityDescription):
    """Describe an ÖkoFEN sensor."""

    kind_of_value: str = "number"  # number | enum_phase | text
    # Without a room sensor the boiler sends 0 instead of a sentinel value.
    zero_is_none: bool = False
    # Values computed from the whole answer instead of one key.
    data_fn: Callable[[OekofenCoordinator], str | int | float | None] | None = None
    attributes_fn: Callable[[OekofenCoordinator], Mapping[str, Any]] | None = None


def _fault_text(coordinator: OekofenCoordinator) -> str | None:
    data = coordinator.data
    if not data.faults:
        return None
    fault = data.faults[0]
    text = f"{fault.text} [{fault.code}]" if fault.code is not None else fault.text
    return text[:STATE_TEXT_MAX]


def _fault_attributes(coordinator: OekofenCoordinator) -> dict[str, Any]:
    data = coordinator.data
    return {
        "faults": [
            {"date": f.date, "text": f.text, "code": f.code} for f in data.faults
        ]
    }


def _temperature(
    kind: str,
    key: str,
    value_key: str,
    *,
    enabled: bool = True,
    diagnostic: bool = False,
) -> OekofenSensorEntityDescription:
    return OekofenSensorEntityDescription(
        key=key,
        translation_key=key,
        kind=kind,
        value_key=value_key,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_registry_enabled_default=enabled,
        entity_category=EntityCategory.DIAGNOSTIC if diagnostic else None,
    )


def _percent(
    kind: str, key: str, value_key: str, *, enabled: bool = True
) -> OekofenSensorEntityDescription:
    return OekofenSensorEntityDescription(
        key=key,
        translation_key=key,
        kind=kind,
        value_key=value_key,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_registry_enabled_default=enabled,
    )


def _status(kind: str) -> OekofenSensorEntityDescription:
    return OekofenSensorEntityDescription(
        key=f"{kind}_status",
        translation_key="status",
        kind=kind,
        value_key="L_statetext",
        kind_of_value="text",
    )


SENSORS: tuple[OekofenSensorEntityDescription, ...] = (
    # Controller
    _temperature("system", "outdoor_temperature", "L_ambient"),
    _temperature("weather", "weather_temperature", "L_temp", enabled=False),
    _percent("weather", "cloud_cover", "L_clouds", enabled=False),
    # Boiler
    _temperature("pe", "boiler_temperature", "L_temp_act"),
    _temperature("pe", "boiler_target_temperature", "L_temp_set"),
    _temperature("pe", "combustion_chamber_temperature", "L_frt_temp_act"),
    _temperature(
        "pe", "combustion_chamber_target_temperature", "L_frt_temp_set", enabled=False
    ),
    _temperature("pe", "external_boiler_sensor", "L_ext_temp", enabled=False),
    _percent("pe", "modulation", "L_modulation"),
    _percent("pe", "flue_gas_fan", "L_fluegas", enabled=False),
    _percent("pe", "combustion_air", "L_currentairflow", enabled=False),
    _percent("pe", "boiler_pump", "L_uw", enabled=False),
    OekofenSensorEntityDescription(
        key="burner_phase",
        translation_key="burner_phase",
        kind="pe",
        value_key="L_state",
        kind_of_value="enum_phase",
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(BURNER_PHASES.values())),
    ),
    _status("pe"),
    OekofenSensorEntityDescription(
        key="fault_message",
        translation_key="fault_message",
        kind="system",
        value_key="L_errors",
        data_fn=_fault_text,
        attributes_fn=_fault_attributes,
    ),
    OekofenSensorEntityDescription(
        key="burner_starts",
        translation_key="burner_starts",
        kind="pe",
        value_key="L_starts",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OekofenSensorEntityDescription(
        key="burner_hours",
        translation_key="burner_hours",
        kind="pe",
        value_key="L_runtime",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    OekofenSensorEntityDescription(
        key="average_runtime",
        translation_key="average_runtime",
        kind="pe",
        value_key="L_avg_runtime",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Burner statistics and energy, computed by the integration (burner.py)
    OekofenSensorEntityDescription(
        key="starts_today",
        translation_key="starts_today",
        kind="pe",
        value_key="L_starts",
        state_class=SensorStateClass.TOTAL_INCREASING,
        data_fn=lambda c: c.tracker.starts_today,
    ),
    OekofenSensorEntityDescription(
        key="runtime_today",
        translation_key="runtime_today",
        kind="pe",
        value_key="L_state",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_display_precision=0,
        data_fn=lambda c: round(c.tracker.runtime_today_min, 1),
    ),
    OekofenSensorEntityDescription(
        key="last_run_duration",
        translation_key="last_run_duration",
        kind="pe",
        value_key="L_state",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_display_precision=0,
        data_fn=lambda c: (
            None if c.tracker.last_run_min is None else round(c.tracker.last_run_min, 1)
        ),
    ),
    OekofenSensorEntityDescription(
        key="short_runs_today",
        translation_key="short_runs_today",
        kind="pe",
        value_key="L_state",
        state_class=SensorStateClass.TOTAL_INCREASING,
        data_fn=lambda c: c.tracker.short_runs_today,
    ),
    OekofenSensorEntityDescription(
        key="heat_energy",
        translation_key="heat_energy",
        kind="pe",
        value_key="L_modulation",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        data_fn=lambda c: round(c.tracker.heat_kwh, 3),
    ),
    OekofenSensorEntityDescription(
        key="pellet_energy",
        translation_key="pellet_energy",
        kind="pe",
        value_key="L_modulation",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        data_fn=lambda c: round(
            c.tracker.pellets_kg * c.energy_model.heating_value_kwh_per_kg, 3
        ),
    ),
    OekofenSensorEntityDescription(
        key="pellet_consumption",
        translation_key="pellet_consumption",
        kind="pe",
        value_key="L_modulation",
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        suggested_display_precision=1,
        data_fn=lambda c: round(c.tracker.pellets_kg, 3),
    ),
    # Heating circuits
    _temperature("hk", "flow_temperature", "L_flowtemp_act"),
    _temperature("hk", "flow_target_temperature", "L_flowtemp_set"),
    OekofenSensorEntityDescription(
        key="room_temperature",
        translation_key="room_temperature",
        kind="hk",
        value_key="L_roomtemp_act",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        zero_is_none=True,
    ),
    _temperature("hk", "room_target_temperature", "L_roomtemp_set", enabled=False),
    _status("hk"),
    # Buffer
    _temperature("pu", "buffer_top_temperature", "L_tpo_act"),
    _temperature("pu", "buffer_middle_temperature", "L_tpm_act"),
    _temperature("pu", "buffer_top_target_temperature", "L_tpo_set", enabled=False),
    _temperature("pu", "buffer_middle_target_temperature", "L_tpm_set", enabled=False),
    _percent("pu", "buffer_pump", "L_pump"),
    _status("pu"),
    # Hot water
    _temperature("ww", "hot_water_temperature", "L_ontemp_act"),
    _temperature("ww", "hot_water_lower_temperature", "L_offtemp_act", enabled=False),
    _temperature("ww", "hot_water_target_temperature", "L_temp_set"),
    _status("ww"),
    # Circulation
    _temperature("circ", "circulation_return_temperature", "L_ret_temp"),
    _temperature(
        "circ",
        "circulation_release_temperature",
        "L_release_temp",
        enabled=False,
        diagnostic=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OekofenConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    async_setup_section_entities(entry, SENSORS, OekofenSensor, async_add_entities)


class OekofenSensor(OekofenEntity, SensorEntity):
    """One value of the boiler."""

    entity_description: OekofenSensorEntityDescription

    def __init__(
        self,
        coordinator: OekofenCoordinator,
        section: str,
        description: OekofenSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, section, description)
        self._last_total: float | None = None

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return extra attributes (list of faults for the fault sensor)."""
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator)

    @property
    def native_value(self) -> str | int | float | None:
        """Return the value in the form Home Assistant expects."""
        value = self._value()
        lifetime_counter = (
            self.state_class is SensorStateClass.TOTAL_INCREASING
            and self.entity_description.data_fn is None
        )
        if lifetime_counter and isinstance(value, int | float):
            # A counter that goes backwards would be read as a reset by the
            # statistics; keep the last value instead (e.g. touch panel restart).
            if self._last_total is not None and value < self._last_total:
                return self._last_total
            self._last_total = value
        return value

    def _value(self) -> str | int | float | None:
        description = self.entity_description
        if description.data_fn is not None:
            return description.data_fn(self.coordinator)
        value = self.raw_value
        match self.entity_description.kind_of_value:
            case "enum_phase":
                return BURNER_PHASES.get(value) if isinstance(value, int) else None
            case "text":
                if not isinstance(value, str) or not value.strip():
                    return None
                text = ", ".join(p.strip() for p in value.split("|") if p.strip())
                return text[:STATE_TEXT_MAX]
        if isinstance(value, bool) or not isinstance(value, int | float):
            return None
        if self.entity_description.zero_is_none and value == 0:
            return None
        if self.native_unit_of_measurement == PERCENTAGE and not 0 <= value <= 100:
            return None
        return value
