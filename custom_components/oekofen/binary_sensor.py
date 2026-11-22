"""Binary sensors for ÖkoFEN Pellematic."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.components.binary_sensor.const import BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import OekofenData, Value
from .const import BURNING_STATES
from .coordinator import OekofenConfigEntry, OekofenCoordinator
from .entity import (
    OekofenEntity,
    OekofenEntityDescription,
    async_setup_section_entities,
)

PARALLEL_UPDATES = 0


def _is_on(value: Value) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value > 0
    return None


def _is_burning(value: Value) -> bool | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value in BURNING_STATES


@dataclass(frozen=True, kw_only=True)
class OekofenBinarySensorEntityDescription(
    OekofenEntityDescription, BinarySensorEntityDescription
):
    """Describe an ÖkoFEN binary sensor."""

    is_on_fn: Callable[[Value], bool | None] = _is_on
    # Computed from the whole answer instead of one key.
    data_fn: Callable[[OekofenData], bool | None] | None = None


def _has_fault(data: OekofenData) -> bool:
    errors = data.get("system", "L_errors")
    count = errors if isinstance(errors, int) and not isinstance(errors, bool) else 0
    return bool(data.faults) or count > 0


def _pump(kind: str, value_key: str = "L_pump") -> OekofenBinarySensorEntityDescription:
    return OekofenBinarySensorEntityDescription(
        key=f"{kind}_pump",
        translation_key="pump",
        kind=kind,
        value_key=value_key,
        device_class=BinarySensorDeviceClass.RUNNING,
    )


BINARY_SENSORS: tuple[OekofenBinarySensorEntityDescription, ...] = (
    # pe.L_br does not show the burner on all models, the phase does.
    OekofenBinarySensorEntityDescription(
        key="burner",
        translation_key="burner",
        kind="pe",
        value_key="L_state",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=_is_burning,
    ),
    OekofenBinarySensorEntityDescription(
        key="fault",
        translation_key="fault",
        kind="system",
        value_key="L_errors",
        device_class=BinarySensorDeviceClass.PROBLEM,
        data_fn=_has_fault,
    ),
    _pump("hk"),
    _pump("ww"),
    _pump("circ", "L_pummp"),  # sic, spelling of the firmware
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OekofenConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    async_setup_section_entities(
        entry, BINARY_SENSORS, OekofenBinarySensor, async_add_entities
    )


class OekofenBinarySensor(OekofenEntity, BinarySensorEntity):
    """On/off value of the boiler."""

    entity_description: OekofenBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: OekofenCoordinator,
        section: str,
        description: OekofenBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, section, description)

    @property
    def is_on(self) -> bool | None:
        """Return True if the pump or burner runs."""
        description = self.entity_description
        if description.data_fn is not None:
            return description.data_fn(self.coordinator.data)
        return description.is_on_fn(self.raw_value)
