from datetime import date
from decimal import Decimal

import pytest

from app.models.fx_rate import FxRate
from app.services import fx_service


@pytest.fixture
def stub_fetch_date(monkeypatch):
    """Replace fetch_rates_for_date with a stub that returns a canned dict."""
    calls: list[date] = []

    async def stub(target: date) -> dict[str, Decimal]:
        calls.append(target)
        return {
            "EUR": Decimal("1.0"),
            "USD": Decimal("1.08"),
            "HUF": Decimal("397.5"),
            "CHF": Decimal("0.96"),
        }

    monkeypatch.setattr(fx_service, "fetch_rates_for_date", stub)
    return calls


@pytest.mark.asyncio
async def test_ensure_rates_for_date_upserts_all_currencies(db_session, stub_fetch_date):
    await fx_service.ensure_rates_for_date(db_session, date(2026, 5, 14))
    rows = db_session.query(FxRate).filter(FxRate.date == date(2026, 5, 14)).all()
    codes = {r.currency for r in rows}
    assert {"EUR", "USD", "HUF", "CHF"}.issubset(codes)
    assert stub_fetch_date == [date(2026, 5, 14)]


@pytest.mark.asyncio
async def test_ensure_rates_for_date_skips_when_already_present(db_session, stub_fetch_date):
    db_session.add(FxRate(currency="EUR", date=date(2026, 5, 14), rate_to_eur=Decimal("1.0")))
    db_session.commit()
    await fx_service.ensure_rates_for_date(db_session, date(2026, 5, 14))
    assert stub_fetch_date == []  # no API call made


@pytest.mark.asyncio
async def test_ensure_rates_swallows_fetch_errors(db_session, monkeypatch):
    async def boom(target):
        raise fx_service.FxFetchError("offline")

    monkeypatch.setattr(fx_service, "fetch_rates_for_date", boom)
    # must not raise — caller's transaction insert must succeed even if FX fails
    await fx_service.ensure_rates_for_date(db_session, date(2026, 5, 14))
    assert db_session.query(FxRate).count() == 0


def test_get_latest_date_returns_none_for_empty_table(db_session):
    assert fx_service.get_latest_date(db_session) is None


def test_get_latest_date_returns_max_date(db_session):
    db_session.add(FxRate(currency="EUR", date=date(2026, 5, 12), rate_to_eur=Decimal("1.0")))
    db_session.add(FxRate(currency="EUR", date=date(2026, 5, 14), rate_to_eur=Decimal("1.0")))
    db_session.commit()
    assert fx_service.get_latest_date(db_session) == date(2026, 5, 14)


def test_rate_lookup(db_session):
    db_session.add(FxRate(currency="CHF", date=date(2026, 5, 14), rate_to_eur=Decimal("0.96")))
    db_session.commit()
    assert fx_service.get_rate(db_session, "CHF", date(2026, 5, 14)) == Decimal("0.96")
    assert fx_service.get_rate(db_session, "USD", date(2026, 5, 14)) is None
    # EUR is always 1.0 even if absent
    assert fx_service.get_rate(db_session, "EUR", date(2026, 5, 14)) == Decimal("1.0")
