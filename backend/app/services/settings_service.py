from datetime import date
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


def _convert(amount: Decimal, old_base: str, new_base: str, db: Session, when: date) -> Decimal:
    if old_base == new_base:
        return amount.quantize(_TWO_PLACES)

    def rate(code: str) -> Decimal | None:
        if code == "EUR":
            return Decimal("1.0")
        return db.execute(
            select(FxRate.rate_to_eur).where(FxRate.currency == code, FxRate.date == when)
        ).scalar_one_or_none()

    r_old = rate(old_base)
    r_new = rate(new_base)
    if r_old is None or r_new is None or r_new == 0:
        raise FxNotAvailableError(
            f"FX rate for {old_base} or {new_base} not available on {when.isoformat()}"
        )
    return (amount * r_old / r_new).quantize(_TWO_PLACES)


def preview_base_currency_change(db: Session, new_base: str) -> dict:
    code = new_base.upper()
    if code not in SUPPORTED_CURRENCIES:
        raise ValueError(f"unknown currency: {new_base!r}")

    old_base = get_settings(db).base_currency
    today = date.today()

    budgets = db.execute(
        select(BudgetLimit, Category.name)
        .join(Category, Category.id == BudgetLimit.category_id)
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
        select(Category).where(Category.target_amount.is_not(None))
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


def commit_base_currency_change(db: Session, new_base: str) -> Settings:
    code = new_base.upper()
    if code not in SUPPORTED_CURRENCIES:
        raise ValueError(f"unknown currency: {new_base!r}")

    old_base = get_settings(db).base_currency
    if old_base == code:
        return get_settings(db)

    today = date.today()

    for b in db.execute(select(BudgetLimit)).scalars().all():
        b.monthly_limit = _convert(b.monthly_limit, old_base, code, db, today)

    for c in db.execute(
        select(Category).where(Category.target_amount.is_not(None))
    ).scalars().all():
        if c.target_amount is not None:
            c.target_amount = _convert(c.target_amount, old_base, code, db, today)

    return set_base_currency(db, code)
