from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.budget_limit import BudgetLimit
from app.models.category import Category
from app.models.fx_rate import FxRate
from app.services import settings_service


def test_get_creates_default_row(db_session):
    s = settings_service.get_settings(db_session)
    assert s.id == 1
    assert s.base_currency == "CHF"


def test_get_is_idempotent(db_session):
    s1 = settings_service.get_settings(db_session)
    s2 = settings_service.get_settings(db_session)
    assert s1.id == s2.id == 1


def test_set_base_currency_valid(db_session):
    settings_service.set_base_currency(db_session, "HUF")
    s = settings_service.get_settings(db_session)
    assert s.base_currency == "HUF"


def test_set_base_currency_rejects_unknown(db_session):
    with pytest.raises(ValueError, match="unknown currency"):
        settings_service.set_base_currency(db_session, "XYZ")


def test_set_base_currency_normalizes_lowercase(db_session):
    settings_service.set_base_currency(db_session, "huf")
    s = settings_service.get_settings(db_session)
    assert s.base_currency == "HUF"


# --- Weekend FX fallback -------------------------------------------------


def test_convert_uses_friday_rate_when_saturday_row_is_missing(db_session):
    """Frankfurter has no weekend rows. _convert must walk back to the most
    recent available date instead of raising FxNotAvailableError. Without this,
    every weekend base-currency change 409s."""
    friday = date(2026, 5, 15)
    saturday = friday + timedelta(days=1)
    # Seed Friday rates only.
    db_session.add(FxRate(currency="USD", date=friday, rate_to_eur=Decimal("1.08")))
    db_session.add(FxRate(currency="CHF", date=friday, rate_to_eur=Decimal("0.96")))
    db_session.commit()

    # No Saturday rows. Conversion should still succeed using Friday's data.
    out = settings_service._convert(
        Decimal("100"), "USD", "CHF", db_session, saturday,
    )
    # 100 USD * 0.96 / 1.08 ≈ 88.89 CHF
    assert out == Decimal("88.89")


def test_convert_raises_when_no_rate_within_fallback_window(db_session):
    """A gap longer than _FX_FALLBACK_DAYS should still raise."""
    far_past = date(2026, 5, 1) - timedelta(days=20)
    db_session.add(FxRate(currency="USD", date=far_past, rate_to_eur=Decimal("1.08")))
    db_session.commit()
    with pytest.raises(settings_service.FxNotAvailableError):
        settings_service._convert(
            Decimal("100"), "USD", "CHF", db_session, date(2026, 5, 1),
        )


# --- Partial-commit rollback ---------------------------------------------


def test_commit_base_currency_change_rollback_on_failure(db_session, monkeypatch):
    """If the DB commit fails after in-memory budget/goal mutations, the
    session must rollback so the dirty objects don't survive into the next
    request (where they would diverge from the DB)."""
    # Seed: a category + budget in CHF base.
    cat = Category(user_id=1, name="Rent", kind="expense", target_amount=Decimal("500"))
    db_session.add(cat); db_session.commit()
    db_session.add(BudgetLimit(
        user_id=1, category_id=cat.id, month="2026-05", monthly_limit=Decimal("500"),
    ))
    today = date.today()
    db_session.add(FxRate(currency="USD", date=today, rate_to_eur=Decimal("1.08")))
    db_session.add(FxRate(currency="CHF", date=today, rate_to_eur=Decimal("0.96")))
    db_session.commit()

    # Force the final db.commit() (via set_base_currency) to raise.
    real_commit = db_session.commit
    call_count = {"n": 0}

    def maybe_failing_commit(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            # This is the commit inside set_base_currency.
            raise RuntimeError("simulated commit failure")
        return real_commit(*args, **kwargs)

    monkeypatch.setattr(db_session, "commit", maybe_failing_commit)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        settings_service.commit_base_currency_change(db_session, "USD", user_id=1)

    # After rollback, the budget should still read the original 500 from DB.
    monkeypatch.setattr(db_session, "commit", real_commit)
    budgets = db_session.execute(
        select_budget := __import__("sqlalchemy").select(BudgetLimit)
    ).scalars().all()
    assert len(budgets) == 1
    assert budgets[0].monthly_limit == Decimal("500")
