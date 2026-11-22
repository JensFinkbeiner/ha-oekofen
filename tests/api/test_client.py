"""Tests for the HTTP client, with a simulated boiler.

The session comes from Home Assistant's AiohttpClientMocker. URLs still pass
through yarl, so the tests also catch query handling problems like the
dropped "?" of "all?".
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from collections.abc import AsyncGenerator
import json
import re
from typing import Any
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)
from yarl import URL

from custom_components.oekofen.api import (
    OekofenAuthError,
    OekofenBusyError,
    OekofenClient,
    OekofenConnectionError,
    OekofenError,
)

HOST = "192.0.2.10"
PORT = 4321
PASSWORD = "s3cret-pw"
BASE = f"http://{HOST}:{PORT}/{PASSWORD}"
URL_ALL = f"{BASE}/all"
URL_META = f"{BASE}/all??"

type Answer = bytes | int | BaseException | tuple[int, bytes]


class FakeBoiler:
    """Queue answers per exact URL and record what was sent."""

    def __init__(self, mocker: AiohttpClientMocker) -> None:
        self._answers: dict[str, deque[Answer]] = defaultdict(deque)
        self.sent: list[str] = []
        self.active = 0
        self.peak = 0
        self.delay = 0.0
        mocker.get(re.compile(".*"), side_effect=self._respond)

    def queue(self, url: str, *answers: Answer) -> None:
        self._answers[url].extend(answers)

    async def _respond(
        self, method: str, url: URL, data: Any
    ) -> AiohttpClientMockResponse:
        self.sent.append(str(url))
        self.active += 1
        self.peak = max(self.peak, self.active)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
        finally:
            self.active -= 1
        queue = self._answers[str(url)]
        answer = queue.popleft() if len(queue) > 1 else queue[0]
        if isinstance(answer, BaseException):
            raise answer
        status, body = (answer, b"") if isinstance(answer, int) else (200, answer)
        if isinstance(answer, tuple):
            status, body = answer
        return AiohttpClientMockResponse(method, url, status=status, response=body)


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


def make_client(session: aiohttp.ClientSession, **kwargs: float) -> OekofenClient:
    kwargs.setdefault("request_gap", 0)
    kwargs.setdefault("busy_retry_delay", 0)
    return OekofenClient(HOST, PORT, PASSWORD, session, **kwargs)


async def test_first_call_reads_metadata_then_all(
    session: aiohttp.ClientSession,
    boiler: FakeBoiler,
    all_bytes: bytes,
    meta_bytes: bytes,
) -> None:
    boiler.queue(URL_META, meta_bytes)
    boiler.queue(URL_ALL, all_bytes)
    client = make_client(session)
    assert not client.has_metadata

    first = await client.async_get_data()
    assert client.has_metadata
    second = await client.async_get_data()
    third = await client.async_get_data(refresh_metadata=True)

    # the question marks must survive URL handling, otherwise no metadata
    assert boiler.sent == [URL_META, URL_ALL, URL_META]
    assert isinstance(first.get("hk1", "L_flowtemp_act"), float)
    # "all" has raw integers, scaled with the cached factor (0.1)
    raw_flow = json.loads(all_bytes)["hk1"]["L_flowtemp_act"]
    assert second.get("hk1", "L_flowtemp_act") == pytest.approx(raw_flow * 0.1)
    assert third.sections.keys() == first.sections.keys()


async def test_busy_is_retried_once(
    session: aiohttp.ClientSession, boiler: FakeBoiler, meta_bytes: bytes
) -> None:
    boiler.queue(URL_META, 401, meta_bytes)
    data = await make_client(session).async_get_data()
    assert data.numbered_sections("pe") == ["pe1"]
    assert len(boiler.sent) == 2


async def test_busy_twice_raises(
    session: aiohttp.ClientSession, boiler: FakeBoiler
) -> None:
    boiler.queue(URL_META, b"Wait at least 2500ms during requests", 401)
    with pytest.raises(OekofenBusyError):
        await make_client(session).async_get_data()
    assert len(boiler.sent) == 2


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (aiohttp.ClientConnectionError(f"failed {URL_META}"), "ClientConnectionError"),
        (TimeoutError(), "Timeout"),
        (500, "HTTP status 500"),
    ],
)
async def test_errors_never_leak_password(
    session: aiohttp.ClientSession,
    boiler: FakeBoiler,
    answer: Answer,
    expected: str,
) -> None:
    boiler.queue(URL_META, answer)
    with pytest.raises(OekofenConnectionError) as info:
        await make_client(session).async_get_data()
    assert expected in str(info.value)
    assert PASSWORD not in str(info.value)
    assert info.value.__cause__ is None
    assert info.value.__context__ is None


async def test_help_page_is_auth_error(
    session: aiohttp.ClientSession, boiler: FakeBoiler
) -> None:
    boiler.queue(URL_META, b"Usage: http://IP:PORT/PASSWORD/all")
    with pytest.raises(OekofenAuthError) as info:
        await make_client(session).async_get_data()
    assert isinstance(info.value, OekofenError)
    assert PASSWORD not in str(info.value)


async def test_requests_keep_the_gap(
    session: aiohttp.ClientSession,
    boiler: FakeBoiler,
    all_bytes: bytes,
    meta_bytes: bytes,
) -> None:
    boiler.queue(URL_META, meta_bytes)
    boiler.queue(URL_ALL, all_bytes)
    client = make_client(session, request_gap=3.0)
    with patch(
        "custom_components.oekofen.api.client.asyncio.sleep", new=AsyncMock()
    ) as sleep:
        await client.async_get_data()
        sleep.assert_not_awaited()
        await client.async_get_data()
    sleep.assert_awaited_once()
    assert sleep.await_args is not None
    assert 2.5 < sleep.await_args.args[0] <= 3.0


async def test_parallel_calls_are_serialized(
    session: aiohttp.ClientSession, boiler: FakeBoiler, meta_bytes: bytes
) -> None:
    boiler.queue(URL_META, meta_bytes)
    boiler.delay = 0.01
    client = make_client(session)
    await asyncio.gather(
        *(client.async_get_data(refresh_metadata=True) for _ in range(3))
    )
    assert boiler.peak == 1
    assert len(boiler.sent) == 3
