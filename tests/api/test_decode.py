"""Tests for decoding and normalizing boiler answers."""

from __future__ import annotations

import json

import pytest

from custom_components.oekofen.api import OekofenAuthError, OekofenParseError
from custom_components.oekofen.api.decode import (
    build_data,
    decode_bytes,
    normalize_scalar,
    parse_faults,
    parse_json,
    parse_meta,
)
from custom_components.oekofen.api.models import FieldMeta, OekofenData


def test_decode_utf8_latin1_and_double_encoding() -> None:
    assert decode_bytes("°C".encode()) == "°C"
    assert decode_bytes("°C".encode("latin-1")) == "°C"
    assert decode_bytes("Â°C".encode()) == "°C"


def test_parse_json_repairs_missing_quote_and_raw_newlines() -> None:
    text = (
        '{"hk1": {"L_statetext: "Heizen", "L_state": 1}, "error": {"error_1": "a\nb"}}'
    )
    data = parse_json(text)
    assert data["hk1"] == {"L_statetext": "Heizen", "L_state": 1}
    assert data["error"]["error_1"] == "a\nb"


def test_parse_json_help_page_is_auth_error() -> None:
    with pytest.raises(OekofenAuthError):
        parse_json("Usage: http://IP:PORT/PASSWORD/all ...")


def test_parse_json_invalid() -> None:
    with pytest.raises(OekofenParseError):
        parse_json('{"a": ')


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("true", True),
        ("false", False),
        (" 215 ", 215),
        ("-3.5", -3.5),
        ("Heizen", "Heizen"),
        (12, 12),
        (1.5, 1.5),
        (None, None),
        ([1], "[1]"),
    ],
)
def test_normalize_scalar(raw: object, expected: object) -> None:
    assert normalize_scalar(raw) == expected


def test_parse_meta_from_real_answer(meta_bytes: bytes) -> None:
    meta = parse_meta(parse_json(decode_bytes(meta_bytes)))
    assert "forecast" not in meta
    flow = meta["hk1"]["L_flowtemp_act"]
    assert flow.factor == 0.1
    assert flow.unit == "°C"
    assert flow.minimum is not None
    assert flow.maximum is not None
    state = meta["pe1"]["L_state"]
    assert state.options
    assert all(isinstance(k, int) for k in state.options)
    assert meta["pe1"]["L_runtimeburner"].factor == 0.01
    # entries without description (plain strings) are skipped
    assert "L_statetext" not in meta["pe1"]


def test_parse_meta_edge_cases() -> None:
    meta = parse_meta(
        {
            "x1": {
                "a": {
                    "val": 1,
                    "factor": "0.5",
                    "unit": "",
                    "format": "0:Aus|bad|1:Ein",
                },
                "b": {"val": 1, "factor": True},
            },
            "plain": 5,
        }
    )
    assert meta["x1"]["a"] == FieldMeta(
        factor=0.5, unit=None, options={0: "Aus", 1: "Ein"}
    )
    assert meta["x1"]["b"].factor == 1
    assert "plain" not in meta


def test_build_data_from_all_with_meta(all_bytes: bytes, meta_bytes: bytes) -> None:
    meta_raw = parse_json(decode_bytes(meta_bytes))
    meta = parse_meta(meta_raw)
    data = build_data(parse_json(decode_bytes(all_bytes)), meta)
    from_meta = build_data(meta_raw, meta)

    raw_all = json.loads(all_bytes)
    assert data.get("hk1", "L_flowtemp_act") == pytest.approx(
        raw_all["hk1"]["L_flowtemp_act"] * 0.1
    )
    assert isinstance(data.get("pe1", "L_starts"), int)
    # privacy: location and forecast are dropped
    assert data.get("weather", "L_location") is None
    assert "forecast" not in data.sections
    assert "pe_info" not in data.sections["pe1"]
    # same keys from both endpoints
    assert set(data.sections) == set(from_meta.sections)
    for section, values in data.sections.items():
        assert set(values) == set(from_meta.sections[section])
    assert data.faults == []
    assert data.numbered_sections("hk") == ["hk1"]
    assert data.numbered_sections("pe") == ["pe1"]
    assert data.field_meta("hk1", "L_flowtemp_act") is meta["hk1"]["L_flowtemp_act"]
    assert data.field_meta("nope", "x") is None


def test_build_data_sentinels_and_scaling() -> None:
    meta = {
        "pe1": {
            "temp": FieldMeta(factor=0.1, unit="°C"),
            "kelvin": FieldMeta(factor=1, unit="K"),
            "starts": FieldMeta(factor=1),
            "hundred": FieldMeta(factor=100),
            "flag": FieldMeta(factor=0.1),
        }
    }
    data = build_data(
        {
            "pe1": {
                "temp": -32768,
                "kelvin": "32767",
                "starts": 32767,
                "hundred": "3",
                "flag": "true",
                "unknown": "12",
            }
        },
        meta,
    )
    assert data.sections["pe1"] == {
        "temp": None,
        "kelvin": None,
        "starts": 32767,
        "hundred": 300,
        "flag": True,
        "unknown": 12,
    }


def test_firmware3_strings_are_scaled() -> None:
    meta = {"hk1": {"L_flowtemp_act": FieldMeta(factor=0.1, unit="°C")}}
    data = build_data({"hk1": {"L_flowtemp_act": "384"}}, meta)
    assert data.get("hk1", "L_flowtemp_act") == 38.4


def test_parse_faults() -> None:
    faults = parse_faults(
        {
            "error_1": "21.11.2026 10:00|Zuendung fehlgeschlagen [2010]",
            "error_2": {"val": "Saugturbine\n blockiert"},
            "error_3": "",
            "L_info": "not an error",
            "error_4": 5,
        }
    )
    assert [(f.date, f.text, f.code) for f in faults] == [
        ("21.11.2026 10:00", "Zuendung fehlgeschlagen", 2010),
        (None, "Saugturbine blockiert", None),
    ]


def test_error_section_in_build_data() -> None:
    data = build_data(
        {"error": {"error_1": "x|Test [1]"}, "system": {"L_errors": 1}}, {}
    )
    assert data.faults[0].code == 1
    assert "error" not in data.sections
    assert data.get("system", "L_errors") == 1


def test_empty_data() -> None:
    data = OekofenData()
    assert data.get("hk1", "x") is None
    assert data.numbered_sections("hk") == []
