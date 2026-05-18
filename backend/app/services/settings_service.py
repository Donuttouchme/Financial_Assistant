from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.budget_limit import BudgetLimit
from app.models.category import Category
from app.models.fx_rate import FxRate
from app.models.settings import Settings
from app.services.currencies import SUPPORTED_CURRENCIES

_SINGLETON_ID = 1
_TWO_PLACES = Decimal("0.01")
# Frankfurter only publishes business-day rates. On a weekend the
# `today` row is absent — fall back to the most recent available row up to
# this many days back. Keeps weekend base-currency changes from 409-ing.
_FX_FALLBACK_DAYS = 7


class FxNotAvailableError(RuntimeError):
    """Raised when a base-currency change is attempted but rates are missing."""


def get_settings(db: Session) -> Settings:
    s = db.execute(select(Settings).where(Settings.id == _SINGLETON_ID)).scalar_one_or_none()
    if s is None:
        s = Settings(id=_SINGLETON_ID, base_currency="CHF")
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def set_base_currency(db: Session, new_base: str) -> Settings:
    code = new_base.upper()
    if code not in SUPPORTED_CURRENCIES:
        raise ValueError(f"unknown currency: {new_base!r}")
    s = get_settings(db)
    s.base_currency = code
    db.commit()
    db.refresh(s)
    return s


def _rate_with_fallback(
    db: Session, currency: str, when: date, *, max_days_back: int = _FX_FALLBACK_DAYS,
) -> Decimal | None:
    """Return the FX rate for ``currency`` on the most recent date at or before
    ``when``, within ``max_days_back`` days. Returns None when no row exists in
    the window. Bridges Frankfurter's weekend/holiday gaps."""
    if currency == "EUR":
        return Decimal("1.0")
    for delta in range(max_days_back + 1):
        d = when - timedelta(days=delta)
        row = db.execute(
            select(FxRate.rate_to_eur).where(FxRate.currency == currency, FxRate.date == d)
        ).scalar_one_or_none()
        if row is not None:
            return row
    return None


def _convert(amount: Decimal, old_base: str, new_base: str, db: Session, when: date) -> Decimal:
    if old_base == new_base:
        return amount.quantize(_TWO_PLACES)

    r_old = _rate_with_fallback(db, old_base, when)
    r_new = _rate_with_fallback(db, new_base, when)
    # rate_to_eur(X) is "1 EUR = X currency-units" (frankfurter convention),
    # so converting old -> new is: amount * r_new / r_old.
    if r_old is None or r_new is None or r_old == 0:
        raise FxNotAvailableError(
            f"FX rate for {old_base} or {new_base} not available on {when.isoformat()}"
        )
    return (amount * r_new / r_old).quantize(_TWO_PLACES)


def preview_base_currency_change(db: Session, new_base: str, user_id: int) -> dict:
    code = new_base.upper()
    if code not in SUPPORTED_CURRENCIES:
        raise ValueError(f"unknown currency: {new_base!r}")

    old_base = get_settings(db).base_currency
    today = date.today()

    budgets = db.execute(
        select(BudgetLimit, Category.name)
        .join(Category, Category.id == BudgetLimit.category_id)
        .where(BudgetLimit.user_id == user_id)
    ).all()
    budget_rows = []
    for b, name in budgets:
        new_amount = _convert(b.monthly_limit, old_base, code, db, today)
        budget_rows.append({
            "category_id": b.category_id,
            "category_name": name,
            "month": b.month,
            "old_amount": str(b.monthly_limit.quantize(_TWO_PLACES)),
            "new_amount": str(new_amount),
        })

    goals = db.execute(
        select(Category)
        .where(Category.user_id == user_id, Category.target_amount.is_not(None))
    ).scalars().all()
    goal_rows = []
    for c in goals:
        if c.target_amount is None:
            continue
        new_amount = _convert(c.target_amount, old_base, code, db, today)
        goal_rows.append({
            "category_id": c.id,
            "category_name": c.name,
            "old_amount": str(c.target_amount.quantize(_TWO_PLACES)),
            "new_amount": str(new_amount),
        })

    return {
        "old_base": old_base,
        "new_base": code,
        "budgets": budget_rows,
        "savings_goals": goal_rows,
    }


def commit_base_currency_change(db: Session, new_base: str, user_id: int) -> Settings:
    code = new_base.upper()
    if code not in SUPPORTED_CURRENCIES:
        raise ValueError(f"unknown currency: {new_base!r}")

    old_base = get_settings(db).base_currency
    if old_base == code:
        return get_settings(db)

    today = date.today()

    # Compute all conversions first so a mid-loop FxNotAvailableError can't
    # leave the session with a partial mutation (rolled back on next request,
    # but explicit is safer than relying on request-scoped teardown).
    budget_updates: list[tuple[BudgetLimit, Decimal]] = []
    for b in db.execute(
        select(BudgetLimit).where(BudgetLimit.user_id == user_id)
    ).scalars().all():
        budget_updates.append((b, _convert(b.monthly_limit, old_base, code, db, today)))

    goal_updates: list[tuple[Category, Decimal]] = []
    for c in db.execute(
        select(Category)
        .where(Category.user_id == user_id, Category.target_amount.is_not(None))
    ).scalars().all():
        if c.target_amount is not None:
            goal_updates.append((c, _convert(c.target_amount, old_base, code, db, today)))

    for b, new_amount in budget_updates:
        b.monthly_limit = new_amount
    for c, new_amount in goal_updates:
        c.target_amount = new_amount

    try:
        return set_base_currency(db, code)
    except Exception:
        # Roll back so the dirty in-memory budget/goal mutations don't survive
        # in the session after a commit failure. SQLAlchemy expires all objects
        # on rollback, so the next read re-fetches from the DB.
        db.rollback()
        raise
