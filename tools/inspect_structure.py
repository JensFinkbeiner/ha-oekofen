"""Describe the structure of captured answers without printing any values.

Usage: python -I tools/inspect_structure.py [stamp]   (default: newest capture)
Output: encoding, JSON validity, sections, keys with value type, and for the
meta answer the metadata fields, factor and unit. Values, texts, min/max and
format strings are never printed.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _conn import RAW_DIR


def decode(raw: bytes) -> tuple[str, str]:
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def kind(v: object) -> str:
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        if re.fullmatch(r"-?\d+", v):
            return "str(int)"
        if re.fullmatch(r"-?\d+\.\d+", v):
            return "str(float)"
        if v in ("true", "false"):
            return "str(bool)"
        return "str"
    return type(v).__name__


def describe(name: str, raw: bytes) -> None:
    text, enc = decode(raw)
    print(
        f"\n=== {name}: {len(raw)} bytes, decoded as {enc}, non-ascii chars: "
        f"{sum(1 for c in text if ord(c) > 127)}, mojibake 'Â': {text.count('Â')}"
    )
    try:
        data = json.loads(text)
        print("JSON: valid")
    except json.JSONDecodeError as err:
        print(f"JSON: invalid ({err.msg} at line {err.lineno} col {err.colno})")
        ctrl = sum(1 for c in text if ord(c) < 32 and c not in "\r\n\t")
        print(
            f"  unquoted L_statetext keys: {len(re.findall(r'[{,]\s*L_statetext\s*:', text))}, "
            f"raw control chars: {ctrl}"
        )
        try:
            data = json.loads(text, strict=False)
            print("  parses with strict=False")
        except json.JSONDecodeError as err2:
            print(f"  still invalid with strict=False: {err2.msg}")
            return
    if not isinstance(data, dict):
        print(f"top level: {type(data).__name__}")
        return
    for section, body in data.items():
        if not isinstance(body, dict):
            print(f"[{section}] {kind(body)}")
            continue
        parts = []
        for key, val in body.items():
            if isinstance(val, dict):
                fields = ",".join(sorted(val))
                extra = ""
                if "factor" in val:
                    extra += f" f={val['factor']}"
                if "unit" in val and val["unit"] not in ("", None):
                    extra += f" u={val['unit']}"
                if "format" in val:
                    extra += " enum"
                parts.append(f"{key}<{kind(val.get('val'))}|{fields}{extra}>")
            else:
                parts.append(f"{key}:{kind(val)}")
        types = Counter(p.split(":")[-1] for p in parts if ":" in p)
        print(f"[{section}] {len(body)} keys {dict(types) if types else ''}")
        print("   " + "  ".join(parts))


def main() -> None:
    files = sorted(RAW_DIR.glob("*.bin"))
    stamp = sys.argv[1] if len(sys.argv) > 1 else files[-1].name.split("_")[0]
    for f in files:
        if f.name.startswith(stamp):
            describe(f.stem.split("_", 1)[1], f.read_bytes())


if __name__ == "__main__":
    main()
