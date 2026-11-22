"""Regression tests for the findings of the review of milestone 0.3.0."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import aiohttp
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.oekofen.api import (
    OekofenAuthError,
    OekofenClient,
    OekofenConnectionError,
    OekofenParseError,
)
from custom_components.oekofen.api.decode import build_data, parse_json
from custom_components.oekofen.api.models import FieldMeta

from .test_client import FakeBoiler


@pytest.fixture
async def session(
    aioclient_mock: AiohttpClientMocker,
) -> AsyncGenerator[aiohttp.ClientSession]:
    sess = aioclient_mock.create_session(asyncio.get_running_loop())
    yield sess
    await sess.close()


@pytest.fixture
def boiler(aioclient_mock: AiohttpClientMocker) -> FakeBoiler:
    return FakeBoiler(aioclient_mock)


@pytest.mark.parametrize("text", ["", "<html><body>Error</body></html>", "  "])
def test_empty_or_html_answer_is_transient(text: str) -> None:
    with pytest.raises(OekofenParseError):
        parse_json(text)


def test_help_page_banner_is_auth_error() -> None:
    with pytest.raises(OekofenAuthError):
        parse_json("Oekofen JSON Interface   V4.00\n...")


def test_percent_sentinel_is_none() -> None:
    data = build_data(
        {"pe1": {"L_modulation": -32768, "L_uw": 55}},
        {"pe1": {"L_modulation": FieldMeta(unit="%"), "L_uw": FieldMeta(unit="%")}},
    )
    assert data.get("pe1", "L_modulation") is None
    assert data.get("pe1", "L_uw") == 55


async def test_password_is_quoted_and_ipv6_bracketed(
    session: aiohttp.ClientSession, boiler: FakeBoiler, meta_bytes: bytes
) -> None:
    url = "http://[2001:db8::10]:4321/a%2Fb%3Fc%23d%20e/all??"
    boiler.queue(url, meta_bytes)
    client = OekofenClient(
        "2001:db8::10", 4321, "a/b?c#d e", session, request_gap=0, busy_retry_delay=0
    )
    await client.async_get_data()
    assert boiler.sent == [url]


async def test_connection_error_has_no_context(
    session: aiohttp.ClientSession, boiler: FakeBoiler
) -> None:
    url = "http://192.0.2.10:4321/pw/all??"
    boiler.queue(url, aiohttp.ClientConnectionError(f"failed {url}"))
    client = OekofenClient("192.0.2.10", 4321, "pw", session, request_gap=0)
    with pytest.raises(OekofenConnectionError) as info:
        await client.async_get_data()
    assert info.value.__cause__ is None
    assert info.value.__context__ is None


async def test_empty_metadata_is_rejected(
    session: aiohttp.ClientSession, boiler: FakeBoiler
) -> None:
    url = "http://192.0.2.10:4321/pw/all??"
    boiler.queue(url, b'{"pe1": {"L_temp_act": 651}}')
    client = OekofenClient("192.0.2.10", 4321, "pw", session, request_gap=0)
    with pytest.raises(OekofenParseError):
        await client.async_get_data()
    assert not client.has_metadata
