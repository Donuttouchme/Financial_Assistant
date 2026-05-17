from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.fx_rate import FxRate
from app.models.transaction import Transaction
from app.schemas.forecast import DailyCumulativeResponse, DailyPoint
from app.services import settings_service
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


_PROFILE_TRAILING_MONTHS = 6


def _months_ago(d: date, months: int) -> date:
    """Subtract `months` calendar months from `d`, clamping the day to the
    target month's last valid day."""
    y, m = d.year, d.month - months
    while m <= 0:
        m += 12
        y -= 1
    last = monthrange(y, m)[1]
    return date(y, m, min(d.day, last))


def day_of_month_profile(
    db: Session,
    *,
    user_id: int,
    category_id: int,
    as_of: date,
) -> list[Decimal]:
    """Normalised 31-element distribution of how this category's expense
    spreads across days-of-month, averaged over the trailing 6 months ending
    the day before `as_of`. Smoothed with a 3-day centered moving average,
    re-normalised to sum to 1.

    Returns a flat 1/31 distribution when the category has no expense history
    in the window (cold-start fallback).

    Amounts are converted to EUR via the FxRate pivot before being binned.
    Missing FX rates are skipped (consistent with `actual_mtd`).
    """
    window_start = _months_ago(as_of, _PROFILE_TRAILING_MONTHS)
    window_end = as_of - timedelta(days=1)

    stmt = (
        select(Transaction)
        .join(Category, Category.id == Transaction.category_id)
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.category_id == category_id,
                Category.kind == "expense",
                Transaction.date >= window_start,
                Transaction.date <= window_end,
            )
        )
    )
    rows = list(db.execute(stmt).scalars().all())

    currencies = {t.currency for t in rows} | {_BASE_CURRENCY}
    dates = {t.date for t in rows}
    rates = _load_rates_for(db, currencies, dates)

    raw = [Decimal(0)] * 31
    for t in rows:
        base_amount = _compute_base_amount(
            amount=t.amount,
            currency=t.currency,
            when=t.date,
            base_currency=_BASE_CURRENCY,
            rate_for=rates,
        )
        if base_amount is None:
            continue
        idx = min(t.date.day, 31) - 1
        raw[idx] += base_amount

    total = sum(raw)
    if total <= 0:
        return [Decimal(1) / 31] * 31

    # Weighted 3-day centered moving average (1:2:1); clamp at boundaries.
    # Centre weight is doubled so isolated-day peaks remain above their neighbours.
    smoothed: list[Decimal] = []
    for i in range(31):
        a = raw[max(0, i - 1)]
        b = raw[i]
        c = raw[min(30, i + 1)]
        smoothed.append((a + 2 * b + c) / 4)

    s = sum(smoothed)
    return [v / s for v in smoothed]


_PROJECTION_WINDOW_DAYS = 90
_PROJECTION_MONTH_DAYS = 30  # Standardised "month length".


def projected_monthly_total(
    db: Session,
    *,
    user_id: int,
    category_id: int,
    as_of: date,
) -> Decimal:
    """Project this category's monthly spend (in EUR) from the trailing 90
    days ending the day before `as_of`. Includes recurring AND ad-hoc — the
    day-of-month profile handles intra-month timing separately, so there is
    no need to disambiguate.

    Returns 0 when the category has no history in the window.
    """
    window_start = as_of - timedelta(days=_PROJECTION_WINDOW_DAYS)
    window_end = as_of - timedelta(days=1)

    stmt = (
        select(Transaction)
        .join(Category, Category.id == Transaction.category_id)
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.category_id == category_id,
                Category.kind == "expense",
                Transaction.date >= window_start,
                Transaction.date <= window_end,
            )
        )
    )
    rows = list(db.execute(stmt).scalars().all())
    if not rows:
        return Decimal(0)

    currencies = {t.currency for t in rows} | {_BASE_CURRENCY}
    dates = {t.date for t in rows}
    rates = _load_rates_for(db, currencies, dates)

    total = Decimal(0)
    for t in rows:
        base_amount = _compute_base_amount(
            amount=t.amount,
            currency=t.currency,
            when=t.date,
            base_currency=_BASE_CURRENCY,
            rate_for=rates,
        )
        if base_amount is None:
            continue
        total += base_amount

    rate_per_day = total / _PROJECTION_WINDOW_DAYS
    return rate_per_day * _PROJECTION_MONTH_DAYS


# ---------------------------------------------------------------------------
# Step 6.1 – cold-start helpers
# ---------------------------------------------------------------------------

_FORECAST_MIN_DAYS = 30
_PROFILE_MIN_DAYS = 60


def expense_history_days(db: Session, *, user_id: int, as_of: date) -> int:
    """Distinct days in the trailing 365 days on which this user recorded
    any expense transaction."""
    window_start = as_of - timedelta(days=365)
    stmt = (
        select(Transaction.date)
        .join(Category, Category.id == Transaction.category_id)
        .where(
            and_(
                Transaction.user_id == user_id,
                Category.kind == "expense",
                Transaction.date >= window_start,
                Transaction.date < as_of,
            )
        )
        .distinct()
    )
    return len(list(db.execute(stmt).all()))


def forecast_available(db: Session, *, user_id: int, as_of: date) -> bool:
    return expense_history_days(db, user_id=user_id, as_of=as_of) >= _FORECAST_MIN_DAYS


def use_profile(db: Session, *, user_id: int, as_of: date) -> bool:
    return expense_history_days(db, user_id=user_id, as_of=as_of) >= _PROFILE_MIN_DAYS


# ---------------------------------------------------------------------------
# Step 6.2 – base-currency conversion helper
# ---------------------------------------------------------------------------

def _eur_to_base_factor(db: Session, *, base_currency: str, on: date) -> Decimal | None:
    """Return the factor F such that `base_amount = eur_amount * F` on date `on`.

    For EUR base, returns 1.0.
    For others, returns 1 / FxRate.rate_to_eur(base, on), or None if missing.
    """
    if base_currency == "EUR":
        return Decimal("1")
    rate = db.execute(
        select(FxRate.rate_to_eur).where(
            FxRate.currency == base_currency, FxRate.date == on
        )
    ).scalar_one_or_none()
    if rate is None or rate == 0:
        return None
    return Decimal("1") / rate


# ---------------------------------------------------------------------------
# Step 6.3 – daily_cumulative composition
# ---------------------------------------------------------------------------

def daily_cumulative(
    db: Session,
    *,
    user_id: int,
    month: str,
    today: date,
    category_id: int | None = None,
) -> DailyCumulativeResponse:
    """Compose per-day cumulative expense for one calendar month.

    Past + today portion uses real transactions via `actual_mtd`. Future
    portion (today+1 → end of month) is projected from each expense
    category's day-of-month profile × projected monthly total, allocated
    over remaining days of the month. The forecast tail is only emitted
    when 30+ days of trailing expense history exist; otherwise future
    points hold the today-MTD value.

    Internal math is in EUR; the response is converted to the user's chosen
    base currency using FX rates on `today` (single factor applied to all
    points for visual consistency across the chart).
    """
    first, last = _month_bounds(month)
    base_currency = settings_service.get_settings(db).base_currency

    mtd_end = min(today, last)
    actuals_eur = actual_mtd(
        db, user_id=user_id, month=month, through=mtd_end, category_id=category_id,
    )

    has_forecast = forecast_available(db, user_id=user_id, as_of=today)
    use_prof = use_profile(db, user_id=user_id, as_of=today)

    # Build per-day forecast contributions (in EUR) for days after today.
    future_per_day_eur: dict[date, Decimal] = {}
    if has_forecast and today < last:
        cat_stmt = select(Category).where(
            Category.user_id == user_id, Category.kind == "expense",
        )
        if category_id is not None:
            cat_stmt = cat_stmt.where(Category.id == category_id)
        for cat in db.execute(cat_stmt).scalars().all():
            projected = projected_monthly_total(
                db, user_id=user_id, category_id=cat.id, as_of=today,
            )
            if projected <= 0:
                continue
            if use_prof:
                profile = day_of_month_profile(
                    db, user_id=user_id, category_id=cat.id, as_of=today,
                )
            else:
                # <60 days history: flat per-day distribution.
                profile = [Decimal("1") / last.day] * 31

            remaining_days = list(range(today.day + 1, last.day + 1))
            if not remaining_days:
                continue
            wsum = sum(profile[d - 1] for d in remaining_days)
            if wsum <= 0:
                continue
            for d in remaining_days:
                share = projected * (profile[d - 1] / wsum)
                day_obj = date(first.year, first.month, d)
                future_per_day_eur[day_obj] = (
                    future_per_day_eur.get(day_obj, Decimal(0)) + share
                )

    # Convert EUR running totals to base currency.
    factor = _eur_to_base_factor(db, base_currency=base_currency, on=today)
    if factor is None:
        # FX rate for base unavailable on `today` — fall through with EUR
        # values labelled as base. The response's base_currency field still
        # reflects user choice, but values may be off by a small amount until
        # rates land. This mirrors the surface UX in the rest of the app.
        factor = Decimal("1")

    points: list[DailyPoint] = []
    running_eur = Decimal(0)
    d = first
    while d <= last:
        if d <= mtd_end:
            running_eur = actuals_eur.get(d, running_eur)
            is_fc = False
        else:
            if has_forecast:
                running_eur += future_per_day_eur.get(d, Decimal(0))
            is_fc = True
        cumulative = (running_eur * factor).quantize(Decimal("0.01"))
        points.append(DailyPoint(date=d, cumulative=cumulative, is_forecast=is_fc))
        d += timedelta(days=1)

    return DailyCumulativeResponse(
        month=month,
        base_currency=base_currency,
        today=today,
        forecast_available=has_forecast,
        points=points,
    )
