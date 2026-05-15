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


def _ensure_expense_category(db: Session, *, user_id: int, category_id: int) -> Category:
    cat = db.execute(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    ).scalar_one_or_none()
    if cat is None:
        raise LookupError(f"Category {category_id} not found for user {user_id}")
    if cat.kind != "expense":
        raise ValueError(
            f"Category {category_id} is kind={cat.kind!r}; "
            "budgets only apply to expense categories"
        )
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
    _ensure_expense_category(db, user_id=user_id, category_id=category_id)
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
    from sqlalchemy import case
    from app.models.fx_rate import FxRate
    from app.services import settings_service

    _validate_month(month)
    start, end = _month_bounds(month)
    base_currency = settings_service.get_settings(db).base_currency

    fx_native = FxRate.__table__.alias("fx_native")
    fx_base = FxRate.__table__.alias("fx_base")

    # EUR is the pivot — treat as 1.0 even when no row exists.
    def _rate_expr(alias, currency_col):
        return case(
            (currency_col == "EUR", Decimal("1.0")),
            else_=alias.c.rate_to_eur,
        )

    base_amount_expr = case(
        (Transaction.currency == base_currency, Transaction.amount),
        (
            (_rate_expr(fx_native, Transaction.currency).is_(None))
            | (_rate_expr(fx_base, base_currency).is_(None)),
            None,
        ),
        else_=Transaction.amount
        * _rate_expr(fx_native, Transaction.currency)
        / _rate_expr(fx_base, base_currency),
    )

    spent_subq = (
        select(
            Transaction.category_id.label("category_id"),
            func.coalesce(func.sum(base_amount_expr), 0).label("spent"),
        )
        .select_from(Transaction)
        .join(
            fx_native,
            (fx_native.c.currency == Transaction.currency)
            & (fx_native.c.date == Transaction.date),
            isouter=True,
        )
        .join(
            fx_base,
            (fx_base.c.currency == base_currency) & (fx_base.c.date == Transaction.date),
            isouter=True,
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
        spent_dec = (Decimal(str(spent)) if spent is not None else Decimal("0")).quantize(two)
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
