"""Guard: fixtures in this public repository contain only placeholder texts."""

from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ALLOWED_PLACEHOLDERS = {"Musterstadt", "Testwetter", "Testname", "Testtext"}
FREE_TEXT_KEYS = {"L_location", "L_source", "name"}


def _load(path: Path) -> dict[str, dict[str, object]]:
    raw = path.read_bytes()
    try:
        return json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(raw.decode("latin-1"))


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.json")), ids=lambda p: p.name)
def test_fixture_has_no_private_text(path: Path) -> None:
    text = path.read_bytes().decode("latin-1")
    assert not re.search(r"\b(?:10|172|192\.168)\.\d+\.\d+", text), (
        "IP address in fixture"
    )
    for section, body in _load(path).items():
        for key, value in body.items():
            val = value.get("val") if isinstance(value, dict) else value
            if key in FREE_TEXT_KEYS:
                assert val in ALLOWED_PLACEHOLDERS, f"{section}.{key} not anonymized"
            if key.startswith("L_w_"):
                assert str(val).startswith("Testvorhersage"), f"{section}.{key}"
