"""Decode and normalize the answers of the ÖkoFEN JSON interface.

Known quirks (see docs/recherche/oekofen-json-api.md):
- no charset header; usually latin-1, sometimes UTF-8, sometimes double encoded
- firmware 4.02 drops the closing quote of "L_statetext
- raw line breaks inside strings (error texts)
- firmware 3.x sends numbers and booleans as strings
- sentinel values for "no sensor"
"""

from __future__ import annotations

import json
import re
from typing import Any

from .exceptions import OekofenAuthError, OekofenParseError
from .models import FieldMeta, OekofenData, OekofenFault, Value

SENTINELS = frozenset({-32768, 32765, 32766, 32767})
# Units whose fields use the sentinel values for "no sensor".
MEASURED_UNITS = frozenset({"°C", "K", "%"})

# Privacy: never keep the location of the weather source or the forecast texts.
DROPPED_SECTIONS = frozenset({"forecast"})
DROPPED_KEYS = frozenset({("weather", "L_location")})

_BROKEN_KEY_RE = re.compile(r'"(L_[A-Za-z0-9_]+):(\s*")')
_INT_RE = re.compile(r"-?\d+")
_FLOAT_RE = re.compile(r"-?\d+\.\d+")
_FAULT_RE = re.compile(
    r"^(?:(?P<date>[^|]*)\|)?(?P<text>.*?)(?:\s*\[(?P<code>\d+)\])?\s*$"
)


def decode_bytes(raw: bytes) -> str:
    """Decode the answer: strict UTF-8 first, latin-1 as fallback."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    # Double encoded degree sign ("Â°C") seen on some firmware versions.
    return text.replace("Â°", "°")


def is_help_page(text: str) -> bool:
    """Return True for the help page ("Oekofen JSON Interface ... usage:")."""
    return text.startswith("Oekofen JSON Interface") or "usage:" in text[:400].lower()


def parse_json(text: str) -> dict[str, Any]:
    """Parse the JSON text, repairing the known firmware bugs."""
    stripped = text.strip()
    if not stripped.startswith("{"):
        if is_help_page(stripped):
            # Wrong password or path: the boiler answers with its help page.
            raise OekofenAuthError(
                "The boiler did not return data (check the JSON password)"
            )
        # Empty body, HTML error page, restart of the touch panel ...: transient.
        raise OekofenParseError("The boiler returned no JSON data")
    repaired = _BROKEN_KEY_RE.sub(r'"\1":\2', stripped)
    try:
        data: dict[str, Any] = json.loads(repaired, strict=False)
    except json.JSONDecodeError as err:
        raise OekofenParseError(
            f"Invalid JSON from the boiler ({err.msg} at line {err.lineno})"
        ) from None
    return data  # a text starting with "{" always parses to a dict


def _parse_options(fmt: str) -> dict[int, str]:
    options: dict[int, str] = {}
    for part in fmt.split("|"):
        number, sep, label = part.partition(":")
        if sep and _INT_RE.fullmatch(number.strip()):
            options[int(number)] = label.strip()
    return options


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return value
    return None


def parse_meta(data: dict[str, Any]) -> dict[str, dict[str, FieldMeta]]:
    """Extract the field descriptions from a metadata answer (all?)."""
    meta: dict[str, dict[str, FieldMeta]] = {}
    for section, body in data.items():
        if not isinstance(body, dict) or section in DROPPED_SECTIONS:
            continue
        fields: dict[str, FieldMeta] = {}
        for key, desc in body.items():
            if not isinstance(desc, dict):
                continue
            factor = _number(normalize_scalar(desc.get("factor", 1)))
            unit = desc.get("unit")
            fmt = desc.get("format")
            fields[key] = FieldMeta(
                factor=factor if factor else 1,
                unit=unit if isinstance(unit, str) and unit else None,
                minimum=_number(normalize_scalar(desc.get("min"))),
                maximum=_number(normalize_scalar(desc.get("max"))),
                options=_parse_options(fmt) if isinstance(fmt, str) else None,
            )
        meta[section] = fields
    return meta


def normalize_scalar(value: Any) -> Value:
    """Convert values of firmware 3.x (strings) into numbers and booleans."""
    if isinstance(value, str):
        text = value.strip()
        if text in ("true", "false"):
            return text == "true"
        if _INT_RE.fullmatch(text):
            return int(text)
        if _FLOAT_RE.fullmatch(text):
            return float(text)
        return value
    if value is None or isinstance(value, bool | int | float):
        return value
    return str(value)


def _scale(value: Value, meta: FieldMeta | None) -> Value:
    if meta is None or isinstance(value, bool) or not isinstance(value, int | float):
        return value
    measured = meta.factor != 1 or meta.unit in MEASURED_UNITS
    if measured and value in SENTINELS:
        return None
    if meta.factor == 1:
        return value
    decimals = max(0, len(f"{meta.factor:.10f}".rstrip("0").split(".")[1]))
    return round(value * meta.factor, decimals)


def parse_faults(section: dict[str, Any]) -> list[OekofenFault]:
    """Parse the section "error" into fault entries (order of the boiler)."""
    faults: list[OekofenFault] = []
    for key, entry in section.items():
        value = entry.get("val") if isinstance(entry, dict) else entry
        if not key.startswith("error") or not isinstance(value, str):
            continue
        raw = " ".join(value.split())
        if not raw:
            continue
        match = _FAULT_RE.match(raw)
        assert match is not None  # the pattern matches every string
        code = match.group("code")
        faults.append(
            OekofenFault(
                raw=raw,
                date=(match.group("date") or "").strip() or None,
                text=match.group("text").strip(),
                code=int(code) if code else None,
            )
        )
    return faults


def build_data(
    data: dict[str, Any], meta: dict[str, dict[str, FieldMeta]]
) -> OekofenData:
    """Normalize a data answer (all or all?) with the given metadata."""
    sections: dict[str, dict[str, Value]] = {}
    faults: list[OekofenFault] = []
    for section, body in data.items():
        if not isinstance(body, dict) or section in DROPPED_SECTIONS:
            continue
        if section == "error":
            faults = parse_faults(body)
            continue
        values: dict[str, Value] = {}
        section_meta = meta.get(section, {})
        for key, raw in body.items():
            if (section, key) in DROPPED_KEYS or key.endswith("_info"):
                continue
            value = raw.get("val") if isinstance(raw, dict) else raw
            values[key] = _scale(normalize_scalar(value), section_meta.get(key))
        sections[section] = values
    return OekofenData(sections=sections, meta=meta, faults=faults)
