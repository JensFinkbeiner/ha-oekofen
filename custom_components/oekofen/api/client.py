"""Async client for the local JSON interface (the only module with network access).

Read-only on purpose: there is no method that writes to the boiler.
"""

from __future__ import annotations

import asyncio
import time

import aiohttp

from .decode import build_data, decode_bytes, parse_json, parse_meta
from .exceptions import OekofenBusyError, OekofenConnectionError
from .models import FieldMeta, OekofenData

# The boiler rejects requests closer than 2.5 s, counted over all clients.
REQUEST_GAP = 3.0
BUSY_RETRY_DELAY = 3.0
TIMEOUT = 20.0

# Metadata answer. The documented form is "all?", but yarl (used by aiohttp)
# drops an empty query, so "all?" would be sent as "all". "all??" keeps the
# question mark and returns the same answer (checked on firmware 4.x,
# 22.11.2026). Some US firmware 3.10 reportedly aborts on "??".
META_PATH = "all??"
DATA_PATH = "all"


class OekofenClient:
    """Read data from one ÖkoFEN boiler."""

    def __init__(
        self,
        host: str,
        port: int,
        password: str,
        session: aiohttp.ClientSession,
        *,
        request_gap: float = REQUEST_GAP,
        busy_retry_delay: float = BUSY_RETRY_DELAY,
        timeout: float = TIMEOUT,
    ) -> None:
        """Initialize the client. The session is owned by the caller."""
        self._base = f"http://{host}:{port}/{password}"
        self._password = password
        self._session = session
        self._request_gap = request_gap
        self._busy_retry_delay = busy_retry_delay
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._lock = asyncio.Lock()
        self._last_request: float | None = None
        self._meta: dict[str, dict[str, FieldMeta]] | None = None

    @property
    def has_metadata(self) -> bool:
        """Return True once the field descriptions have been loaded."""
        return self._meta is not None

    async def async_get_data(self, *, refresh_metadata: bool = False) -> OekofenData:
        """Return the current values of all sections.

        The first call (or refresh_metadata=True) reads the metadata answer, which also
        contains factors, units and enum labels. Later calls read the smaller
        "all" and reuse the cached descriptions.
        """
        if self._meta is None or refresh_metadata:
            raw = parse_json(decode_bytes(await self._request(META_PATH)))
            self._meta = parse_meta(raw)
            return build_data(raw, self._meta)
        raw = parse_json(decode_bytes(await self._request(DATA_PATH)))
        return build_data(raw, self._meta)

    async def _request(self, path: str) -> bytes:
        """Send one GET request, serialized and rate limited, with one busy retry."""
        async with self._lock:
            try:
                return await self._request_once(path)
            except OekofenBusyError:
                await asyncio.sleep(self._busy_retry_delay)
                return await self._request_once(path)

    async def _request_once(self, path: str) -> bytes:
        if self._last_request is not None:
            wait = self._request_gap - (time.monotonic() - self._last_request)
            if wait > 0:
                await asyncio.sleep(wait)
        try:
            async with self._session.get(
                f"{self._base}/{path}", timeout=self._timeout
            ) as resp:
                body = await resp.read()
                status = resp.status
        except TimeoutError:
            raise OekofenConnectionError(
                "Timeout while talking to the boiler"
            ) from None
        except aiohttp.ClientError as err:
            # aiohttp messages can contain the URL, which contains the password.
            raise OekofenConnectionError(
                f"Cannot connect to the boiler ({type(err).__name__})"
            ) from None
        finally:
            self._last_request = time.monotonic()
        if status == 401 or b"Wait at least" in body[:200]:
            raise OekofenBusyError("The boiler is busy (rate limit)")
        if status != 200:
            raise OekofenConnectionError(
                f"Unexpected HTTP status {status} from the boiler"
            )
        return body
