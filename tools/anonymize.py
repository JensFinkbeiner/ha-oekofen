"""Turn the newest capture in local/raw/ into anonymized test fixtures.

Usage: python -I tools/anonymize.py
Writes tests/fixtures/all.json (encoding of the original kept) and
tests/fixtures/all_meta.json (latin-1 like the boiler). Prints only a summary.

What is replaced:
- every free-text string except boiler status texts, enum formats, units and
  the *_info descriptions (location, weather source, forecast, circuit names)
- counters that identify the individual boiler (starts, runtime hours)
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _conn import RAW_DIR, ROOT

FIXTURES = ROOT / "tests" / "fixtures"
KEEP_STRING_KEYS = {"L_statetext"}
PLACEHOLDERS = {
    "L_location": "Musterstadt",
    "L_source": "Testwetter",
    "name": "Testname",
}
COUNTERS = {"L_starts": 12345, "L_runtime": 6789}


def decode(raw: bytes) -> tuple[str, str]:
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def scrub_value(key: str, value: object) -> object:
    if isinstance(value, str):
        if key in KEEP_STRING_KEYS or key.endswith("_info"):
            return value
        if key in PLACEHOLDERS:
            return PLACEHOLDERS[key]
        if key.startswith("L_w_"):
            return f"Testvorhersage {key.removeprefix('L_w_')}"
        return "Testtext"
    if key in COUNTERS and isinstance(value, int):
        return COUNTERS[key]
    return value


def scrub(
    data: dict[str, dict[str, object]],
) -> tuple[dict[str, dict[str, object]], int]:
    changed = 0
    for body in data.values():
        if not isinstance(body, dict):
            continue
        for key, val in body.items():
            if isinstance(val, dict) and "val" in val:
                new = scrub_value(key, val["val"])
                changed += new != val["val"]
                val["val"] = new
            else:
                new = scrub_value(key, val)
                changed += new != val
                body[key] = new
    return data, changed


def main() -> None:
    stamp = sorted(RAW_DIR.glob("*_all.bin"))[-1].name.split("_")[0]
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for name in ("all", "all_meta"):
        text, enc = decode((RAW_DIR / f"{stamp}_{name}.bin").read_bytes())
        data, changed = scrub(json.loads(text))
        out = json.dumps(data, ensure_ascii=False, indent=1)
        (FIXTURES / f"{name}.json").write_bytes(out.encode(enc))
        print(f"{name}.json: {enc}, {changed} values replaced")


if __name__ == "__main__":
    main()
