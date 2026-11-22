"""Base entity, devices and dynamic entity creation for ÖkoFEN Pellematic."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import re

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import ChildDeviceInfo, DeviceInfo
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import OekofenData, Value
from .const import DEFAULT_TITLE, DOMAIN, MANUFACTURER
from .coordinator import OekofenConfigEntry, OekofenCoordinator

# Section prefix -> translation key of the child device. "pe1" is the main device.
CHILD_DEVICES: dict[str, str] = {
    "pe": "boiler",
    "hk": "heating_circuit",
    "pu": "buffer",
    "ww": "hot_water",
    "circ": "circulation",
    "sk": "solar",
}
# Sections without a number, shown on the main device.
MAIN_SECTIONS = frozenset({"system", "weather"})
MAIN_BOILER = "pe1"

_SECTION_RE = re.compile(r"^([a-z]+?)(\d+)$")


@dataclass(frozen=True, kw_only=True)
class OekofenEntityDescription(EntityDescription):
    """Describe one value of a section kind (e.g. "hk" for all heating circuits)."""

    kind: str
    value_key: str


def main_device_identifier(entry: OekofenConfigEntry) -> tuple[str, str]:
    """Return the device identifier of the controller (main device)."""
    return (DOMAIN, entry.entry_id)


def section_device_identifier(
    entry: OekofenConfigEntry, section: str
) -> tuple[str, str]:
    """Return the device identifier of the device that shows one section."""
    if section in MAIN_SECTIONS or section == MAIN_BOILER:
        return main_device_identifier(entry)
    return (DOMAIN, f"{entry.entry_id}_{section}")


@callback
def async_register_main_device(
    hass: HomeAssistant, entry: OekofenConfigEntry, data: OekofenData
) -> str:
    """Register the controller as main device and return its device id.

    Child devices (ChildDeviceInfo) reference the parent by device id, so the
    main device must exist before the platforms add entities.
    """
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={main_device_identifier(entry)},
        manufacturer=MANUFACTURER,
        model=boiler_model(data),
        name=DEFAULT_TITLE,
    )
    return device.id


def device_info(
    coordinator: OekofenCoordinator, section: str
) -> DeviceInfo | ChildDeviceInfo:
    """Return the device of a section: main device or a child device."""
    entry = coordinator.config_entry
    identifier = section_device_identifier(entry, section)
    if identifier == main_device_identifier(entry):
        return DeviceInfo(identifiers={identifier})
    match = _SECTION_RE.match(section)
    kind, index = (match.group(1), match.group(2)) if match else (section, "")
    return ChildDeviceInfo(
        identifiers={identifier},
        parent_device_id=entry.runtime_data.main_device_id,
        translation_key=CHILD_DEVICES.get(kind, "section"),
        translation_placeholders={"index": index, "section": section},
    )


def boiler_model(data: OekofenData) -> str | None:
    """Return the boiler type from its enum text, e.g. "COMPACT"."""
    value = data.get(MAIN_BOILER, "L_type")
    meta = data.field_meta(MAIN_BOILER, "L_type")
    if isinstance(value, int) and meta and meta.options:
        return meta.options.get(value)
    return None


def sections_for_kind(data: OekofenData, kind: str) -> list[str]:
    """Return the present sections for a description kind."""
    if kind in MAIN_SECTIONS:
        return [kind] if kind in data.sections else []
    return data.numbered_sections(kind)


class OekofenEntity(CoordinatorEntity[OekofenCoordinator]):
    """Base class: one value of one section."""

    _attr_has_entity_name = True
    entity_description: OekofenEntityDescription

    def __init__(
        self,
        coordinator: OekofenCoordinator,
        section: str,
        description: OekofenEntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self.section = section
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{section}_{description.key}"
        )
        self._attr_device_info = device_info(coordinator, section)

    @property
    def available(self) -> bool:
        """Unavailable if the boiler stopped sending this value."""
        return super().available and (
            self.entity_description.value_key
            in self.coordinator.data.sections.get(self.section, {})
        )

    @property
    def raw_value(self) -> Value:
        """Return the normalized value from the boiler."""
        return self.coordinator.data.get(
            self.section, self.entity_description.value_key
        )


def async_setup_section_entities[D: OekofenEntityDescription](
    entry: OekofenConfigEntry,
    descriptions: Iterable[D],
    factory: Callable[[OekofenCoordinator, str, D], Entity],
    async_add_entities: Callable[[Iterable[Entity]], None],
) -> None:
    """Add entities for all present sections, and later for new sections."""
    coordinator = entry.runtime_data.coordinator
    descriptions = tuple(descriptions)
    known: set[tuple[str, str]] = set()

    @callback
    def _add_new() -> None:
        data = coordinator.data
        new: list[Entity] = []
        for description in descriptions:
            for section in sections_for_kind(data, description.kind):
                key = (section, description.key)
                if key in known or description.value_key not in data.sections[section]:
                    continue
                known.add(key)
                new.append(factory(coordinator, section, description))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))
