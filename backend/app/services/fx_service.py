"""FX service.

Layer A (this task): low-level frankfurter.app HTTP client.
Layer B (Task 4):   high-level orchestration — ensure_rates_for_date,
                    refresh_today, status. Imports the layer-A helpers.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx

FRANKFURTER_BASE_URL = "https://api.frankfurter.app"
_HTTP_TIMEOUT_SECONDS = 8.0


class FxFetchError(RuntimeError):
    """Raised when frankfurter.app responds with a non-2xx status."""


def _parse_response(payload: dict) -> dict[str, Decimal]:
    rates_raw = payload.get("rates") or {}
    result: dict[str, Decimal] = {"EUR": Decimal("1.0")}  # base is always 1
    for code, value in rates_raw.items():
        result[code] = Decimal(str(value))
    return result


async def fetch_rates_for_date(target: date) -> dict[str, Decimal]:
    iso = target.isoformat()
    url = f"{FRANKFURTER_BASE_URL}/{iso}"
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(url)
    if response.status_code != 200:
        raise FxFetchError(
            f"frankfurter.app returned {response.status_code} for {iso}: {response.text[:200]}"
        )
    return _parse_response(response.json())


async def fetch_rates_for_today() -> dict[str, Decimal]:
    url = f"{FRANKFURTER_BASE_URL}/latest"
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(url)
    if response.status_code != 200:
        raise FxFetchError(
            f"frankfurter.app returned {response.status_code} for latest: {response.text[:200]}"
        )
    return _parse_response(response.json())
