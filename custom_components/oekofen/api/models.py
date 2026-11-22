"""Data model of the ÖkoFEN JSON interface."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

type Value = int | float | bool | str | None

_SECTION_RE = re.compile(r"^([a-z_]+?)(\d+)$")


@dataclass(frozen=True, slots=True)
class FieldMeta:
    """Description of one field, taken from the metadata answer (all?)."""

    factor: float = 1
    unit: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    options: dict[int, str] | None = None


@dataclass(frozen=True, slots=True)
class OekofenFault:
    """One entry of the section "error" (format "date|text [code]")."""

    raw: str
    date: str | None
    text: str
    code: int | None


@dataclass(slots=True)
class OekofenData:
    """Normalized answer of the boiler.

    Values are scaled with their factor, sentinel values ("no sensor") are
    None, and booleans or numbers sent as strings are converted.
    """

    sections: dict[str, dict[str, Value]] = field(default_factory=dict)
    meta: dict[str, dict[str, FieldMeta]] = field(default_factory=dict)
    faults: list[OekofenFault] = field(default_factory=list)

    def get(self, section: str, key: str) -> Value:
        """Return one value, or None if the section or key does not exist."""
        return self.sections.get(section, {}).get(key)

    def field_meta(self, section: str, key: str) -> FieldMeta | None:
        """Return the metadata of one field, if known."""
        return self.meta.get(section, {}).get(key)

    def numbered_sections(self, prefix: str) -> list[str]:
        """Return the present sections of one kind, e.g. ["hk1", "hk2"]."""
        found = []
        for name in self.sections:
            match = _SECTION_RE.match(name)
            if match and match.group(1) == prefix:
                found.append((int(match.group(2)), name))
        return [name for _, name in sorted(found)]
