"""Fixtures for the protocol tests. Based on anonymized answers of a real boiler."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture
def all_bytes() -> bytes:
    """Answer of /all (UTF-8, values only)."""
    return (FIXTURES / "all.json").read_bytes()


@pytest.fixture
def meta_bytes() -> bytes:
    """Answer of /all? (latin-1, values with descriptions)."""
    return (FIXTURES / "all_meta.json").read_bytes()
