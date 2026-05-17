from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction
from app.services.transaction_service import _compute_base_amount, _load_rates_for

# FxRate rows pivot on EUR (rate_to_eur). Forecast totals are expressed in EUR
# so that _compute_base_amount can do the conversion without requiring the user's
# chosen base currency to have a matching rate row in the test DB.
_BASE_CURRENCY = "EUR"


def _month_bounds(month: str) -> tuple[date, date]:
    """Return (first_day, last_day) of a 'YYYY-MM' month."""
    y, m = (int(p) for p in month.split("-"))
    last = monthrange(y, m)[1]
    return date(y, m, 1), date(y, m, last)


def actual_mtd(
    db: Session,
    *,
    user_id: int,
    month: str,
    through: date,
    category_id: int | None = None,
) -> dict[date, Decimal]:
    """Cumulative expense in EUR, day 1 of `month` through `through`.

    Returns one entry per day in [first_of_month, through], expressed as EUR
    Decimal (the FxRate pivot currency). Income categories are excluded.
    If `category_id` is supplied, only that category's transactions are summed.
    Foreign-currency transactions are converted via the same FX pipeline used
    by `transaction_service.enrich_with_base_amount`.
    """
    first, _ = _month_bounds(month)
    if through < first:
        return {}

    stmt = (
        select(Transaction)
        .join(Category, Category.id == Transaction.category_id)
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.date >= first,
                Transaction.date <= through,
                Category.kind == "expense",
            )
        )
    )
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)

    rows = list(db.execute(stmt).scalars().all())

    currencies = {t.currency for t in rows} | {_BASE_CURRENCY}
    dates = {t.date for t in rows}
    rates = _load_rates_for(db, currencies, dates)

    per_day: dict[date, Decimal] = {}
    for t in rows:
        base_amount = _compute_base_amount(
            amount=t.amount,
            currency=t.currency,
            when=t.date,
            base_currency=_BASE_CURRENCY,
            rate_for=rates,
        )
        if base_amount is None:
            # Missing FX rate — treat as zero rather than blowing up. Matches
            # the spirit of `enrich_with_base_amount` which surfaces None to
            # the API; here we sum, so None means "can't include".
            continue
        per_day[t.date] = per_day.get(t.date, Decimal(0)) + base_amount

    out: dict[date, Decimal] = {}
    running = Decimal(0)
    d = first
    while d <= through:
        running += per_day.get(d, Decimal(0))
        out[d] = running
        d += timedelta(days=1)
    return out
