"""Practice test: read the real boiler with the real client (aiohttp).

Usage: docker compose -f devenv/compose.yaml run --rm tools uv run python tools/live_check.py
Reads metadata, waits, reads data twice. Prints only counts, durations and
error types, never values.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import time

import aiohttp

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from _conn import connection, mask  # noqa: E402

from custom_components.oekofen.api import OekofenClient, OekofenData, OekofenError  # noqa: E402


def summary(label: str, data: OekofenData, took: float) -> None:
    values = sum(len(v) for v in data.sections.values())
    missing = sum(1 for v in data.sections.values() for x in v.values() if x is None)
    scaled = sum(
        1 for v in data.sections.values() for x in v.values() if isinstance(x, float)
    )
    with_meta = sum(len(v) for v in data.meta.values())
    print(
        f"{label}: {took:.2f} s, {len(data.sections)} sections "
        f"({', '.join(data.sections)}), {values} values, {scaled} scaled, "
        f"{missing} without sensor, {with_meta} field descriptions, "
        f"{len(data.faults)} faults"
    )


async def main() -> None:
    host, port, password = connection()
    async with aiohttp.ClientSession() as session:
        client = OekofenClient(host, port, password, session)
        for label, refresh in (
            ("metadata (all??)", True),
            ("data (all)", False),
            ("data (all)", False),
        ):
            start = time.monotonic()
            try:
                data = await client.async_get_data(refresh_metadata=refresh)
            except OekofenError as err:
                print(
                    f"{label}: {type(err).__name__}: {mask(str(err), password, host)}"
                )
                continue
            summary(label, data, time.monotonic() - start)


if __name__ == "__main__":
    asyncio.run(main())
