"""Guard: fixtures in this public repository contain only placeholder texts."""

from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ALLOWED_PLACEHOLDERS = {"Musterstadt", "Testwetter", "Testname", "Testtext"}
FREE_TEXT_KEYS = {"L_location", "L_source", "name"}
# RFC 5737 documentation networks.
DOC_NETS = ("192.0.2.", "198.51.100.", "203.0.113.")


def _load(path: Path) -> dict[str, dict[str, object]]:
    raw = path.read_bytes()
    try:
        return json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(raw.decode("latin-1"))


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.json")), ids=lambda p: p.name)
def test_fixture_has_no_private_text(path: Path) -> None:
    text = path.read_bytes().decode("latin-1")
    for ip in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text):
        assert ip.startswith(DOC_NETS), f"IP address {ip} in fixture"
    assert not re.search(r'"(?:lat|lon|latitude|longitude|serial)', text, re.I)
    for section, body in _load(path).items():
        for key, value in body.items():
            val = value.get("val") if isinstance(value, dict) else value
            if key in FREE_TEXT_KEYS:
                assert val in ALLOWED_PLACEHOLDERS, f"{section}.{key} not anonymized"
            if key.startswith("L_w_"):
                assert str(val).startswith("Testvorhersage"), f"{section}.{key}"
