"""Capture raw answers of the boiler into local/raw/ (never committed).

Usage (from the repository root): python -I tools/capture.py
Prints only status, size and duration, never the content.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _conn import RAW_DIR, connection, mask

ENDPOINTS = {"all": "all", "all_meta": "all?", "error": "error"}
GAP_SECONDS = 5
RETRY_SECONDS = 4


def fetch(url: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def main() -> None:
    host, port, password = connection()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for i, (name, path) in enumerate(ENDPOINTS.items()):
        if i:
            time.sleep(GAP_SECONDS)
        url = f"http://{host}:{port}/{password}/{path}"
        for attempt in (1, 2):
            start = time.monotonic()
            try:
                status, body = fetch(url)
            except Exception as exc:
                print(f"{name}: {mask(f'{type(exc).__name__}: {exc}', password, host)}")
                break
            took = time.monotonic() - start
            busy = status == 401 or b"Wait at least" in body[:200]
            if busy and attempt == 1:
                print(f"{name}: busy (status {status}), retry in {RETRY_SECONDS} s")
                time.sleep(RETRY_SECONDS)
                continue
            out = RAW_DIR / f"{stamp}_{name}.bin"
            out.write_bytes(body)
            print(
                f"{name}: status {status}, {len(body)} bytes, {took:.2f} s -> {out.name}"
            )
            break


if __name__ == "__main__":
    main()
