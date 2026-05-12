import re
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.budget_limit import BudgetLimit
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.budget_limit import BudgetWithSpendingRow

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _validate_month(month: str) -> None:
    if not _MONTH_RE.match(month):
        raise ValueError(f"month must be YYYY-MM, got {month!r}")


def _ensure_category(db: Session, *, user_id: int, category_id: int) -> Category:
    cat = db.execute(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    ).scalar_one_or_none()
    if cat is None:
        raise LookupError(f"Category {category_id} not found for user {user_id}")
    return cat


def set_budget(
    db: Session,
    *,
    user_id: int,
    category_id: int,
    month: str,
    monthly_limit: Decimal,
) -> BudgetLimit:
    _validate_month(month)
    _ensure_category(db, user_id=user_id, category_id=category_id)
    monthly_limit = monthly_limit.quantize(Decimal("0.01"))

    existing = db.execute(
        select(BudgetLimit).where(
            BudgetLimit.user_id == user_id,
            BudgetLimit.category_id == category_id,
            BudgetLimit.month == month,
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.monthly_limit = monthly_limit
        db.commit()
        db.refresh(existing)
        return existing

    budget = BudgetLimit(
        user_id=user_id, category_id=category_id, month=month, monthly_limit=monthly_limit
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def _month_bounds(month: str):
    from datetime import date
    year, mo = map(int, month.split("-"))
    start = date(year, mo, 1)
    end = date(year + (mo // 12), (mo % 12) + 1, 1)
    return start, end


def list_budgets_with_spending(
    db: Session, *, user_id: int, month: str
) -> list[BudgetWithSpendingRow]:
    _validate_month(month)
    start, end = _month_bounds(month)

    spent_subq = (
        select(
            Transaction.category_id.label("category_id"),
            func.coalesce(func.sum(Transaction.amount), 0).label("spent"),
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.date >= start,
            Transaction.date < end,
        )
        .group_by(Transaction.category_id)
        .subquery()
    )

    rows = db.execute(
        select(BudgetLimit, Category.name, spent_subq.c.spent)
        .join(Category, Category.id == BudgetLimit.category_id)
        .outerjoin(spent_subq, spent_subq.c.category_id == BudgetLimit.category_id)
        .where(BudgetLimit.user_id == user_id, BudgetLimit.month == month)
    ).all()

    two = Decimal("0.01")
    result: list[BudgetWithSpendingRow] = []
    for budget, cat_name, spent in rows:
        spent_dec = (Decimal(spent) if spent is not None else Decimal("0")).quantize(two)
        limit = budget.monthly_limit.quantize(two)
        overage = (spent_dec - limit).quantize(two) if spent_dec > limit else Decimal("0.00")
        result.append(
            BudgetWithSpendingRow(
                category_id=budget.category_id,
                category_name=cat_name,
                month=budget.month,
                monthly_limit=limit,
                spent=spent_dec,
                over_budget=spent_dec > limit,
                overage=overage,
            )
        )
    return result
