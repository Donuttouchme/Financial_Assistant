"""FX service.

Layer A (this task): low-level frankfurter.app HTTP client.
Layer B (Task 4):   high-level orchestration — ensure_rates_for_date,
                    refresh_today, status. Imports the layer-A helpers.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models.fx_rate import FxRate

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
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
    except httpx.HTTPError as exc:
        raise FxFetchError(f"frankfurter.app request failed for {iso}: {exc}") from exc
    if response.status_code != 200:
        raise FxFetchError(
            f"frankfurter.app returned {response.status_code} for {iso}: {response.text[:200]}"
        )
    return _parse_response(response.json())


async def fetch_rates_for_today() -> dict[str, Decimal]:
    url = f"{FRANKFURTER_BASE_URL}/latest"
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
    except httpx.HTTPError as exc:
        raise FxFetchError(f"frankfurter.app request failed for latest: {exc}") from exc
    if response.status_code != 200:
        raise FxFetchError(
            f"frankfurter.app returned {response.status_code} for latest: {response.text[:200]}"
        )
    return _parse_response(response.json())


def get_latest_date(db: Session) -> date | None:
    return db.execute(select(func.max(FxRate.date))).scalar_one_or_none()


def get_rate(db: Session, currency: str, when: date) -> Decimal | None:
    """Return the rate row's value for (currency, when). EUR is always 1.0."""
    if currency == "EUR":
        return Decimal("1.0")
    return db.execute(
        select(FxRate.rate_to_eur).where(FxRate.currency == currency, FxRate.date == when)
    ).scalar_one_or_none()


def _has_any_row_for_date(db: Session, when: date) -> bool:
    return db.execute(
        select(FxRate.currency).where(FxRate.date == when).limit(1)
    ).first() is not None


def _upsert_rates(db: Session, when: date, rates: dict[str, Decimal]) -> int:
    """Insert OR IGNORE per (currency, date). Returns number of upserted rows."""
    rows = [
        {"currency": code, "date": when, "rate_to_eur": rate}
        for code, rate in rates.items()
    ]
    if not rows:
        return 0
    stmt = sqlite_insert(FxRate).values(rows)
    # On conflict (currency, date), keep the existing row — first fetch wins.
    stmt = stmt.on_conflict_do_nothing(index_elements=["currency", "date"])
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0


async def ensure_rates_for_date(db: Session, when: date) -> None:
    """Eager fill: if no rate rows exist for `when`, fetch from frankfurter and upsert.

    Idempotent. Swallows FxFetchError so callers (transaction insert, CSV import,
    etc.) don't fail when offline — the rates will be filled on next refresh.
    """
    if _has_any_row_for_date(db, when):
        return
    try:
        rates = await fetch_rates_for_date(when)
    except FxFetchError:
        return
    _upsert_rates(db, when, rates)


async def refresh_today(db: Session) -> tuple[date | None, int]:
    """Fetch /latest and upsert. Returns (fetched_date, currencies_updated).

    Used by lifespan startup and by POST /api/fx/refresh.
    """
    try:
        rates = await fetch_rates_for_today()
    except FxFetchError:
        return (None, 0)
    when = date.today()
    count = _upsert_rates(db, when, rates)
    return (when, count)


async def ensure_rates_for_dates(db: Session, dates: Iterable[date]) -> None:
    for d in set(dates):
        await ensure_rates_for_date(db, d)
