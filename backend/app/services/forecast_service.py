from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.forecast import DailyCumulativeResponse, DailyPoint, MonthlyBucketsResponse, MonthlyPoint
from app.services import settings_service
from app.services.transaction_service import _compute_base_amount, _load_rates_for


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
    base_currency: str,
    category_id: int | None = None,
) -> dict[date, Decimal]:
    """Cumulative expense in `base_currency`, day 1 of `month` through `through`.

    Same-currency transactions are summed directly with no FX lookup — this is
    what `_compute_base_amount` does when `currency == base_currency`. Foreign-
    currency transactions need rate rows for both the tx currency AND the base
    on the tx date; missing rates → that single transaction is skipped. The
    forecast intentionally accounts in the user's chosen base currency rather
    than routing through EUR, because old transaction dates frequently lack FX
    rows and an EUR pivot would force them all through CHF→EUR→CHF and drop
    every single one.
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

    currencies = {t.currency for t in rows} | {base_currency}
    dates = {t.date for t in rows}
    rates = _load_rates_for(db, currencies, dates)

    per_day: dict[date, Decimal] = {}
    for t in rows:
        base_amount = _compute_base_amount(
            amount=t.amount,
            currency=t.currency,
            when=t.date,
            base_currency=base_currency,
            rate_for=rates,
        )
        if base_amount is None:
            # Missing FX rate for a cross-currency tx — skip. Same-currency tx
            # never hit this branch (the helper shortcuts before any lookup).
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
    base_currency: str,
) -> list[Decimal]:
    """Normalised 31-element distribution of how this category's expense
    spreads across days-of-month, averaged over the trailing 6 months ending
    the day before `as_of`. Smoothed with a 3-day centered moving average,
    re-normalised to sum to 1.

    Returns a flat 1/31 distribution when the category has no expense history
    in the window (cold-start fallback).

    Amounts are converted to `base_currency` via `_compute_base_amount`. Same-
    currency transactions skip FX entirely; cross-currency transactions whose
    date lacks an FX row are skipped.
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

    currencies = {t.currency for t in rows} | {base_currency}
    dates = {t.date for t in rows}
    rates = _load_rates_for(db, currencies, dates)

    raw = [Decimal(0)] * 31
    for t in rows:
        base_amount = _compute_base_amount(
            amount=t.amount,
            currency=t.currency,
            when=t.date,
            base_currency=base_currency,
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
    base_currency: str,
) -> Decimal:
    """Project this category's monthly spend (in `base_currency`) from the
    trailing 90 days ending the day before `as_of`. Includes recurring AND
    ad-hoc — the day-of-month profile handles intra-month timing separately,
    so there is no need to disambiguate.

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

    currencies = {t.currency for t in rows} | {base_currency}
    dates = {t.date for t in rows}
    rates = _load_rates_for(db, currencies, dates)

    total = Decimal(0)
    for t in rows:
        base_amount = _compute_base_amount(
            amount=t.amount,
            currency=t.currency,
            when=t.date,
            base_currency=base_currency,
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
    """True when the user has any expense history at all.

    Flips the empty-state placeholder on the dashboard widget / forecast page
    when there's literally nothing to show. We always run the forecast math
    regardless of how thin the history is — the day-of-month profile falls
    back to a flat distribution when a category has no past spend, and the
    monthly projection naturally returns zero when there's no trailing data.
    """
    return expense_history_days(db, user_id=user_id, as_of=as_of) > 0


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
    portion (today+1 -> end of month) is projected from each expense
    category's day-of-month profile x projected monthly total, allocated
    over remaining days of the month. The forecast is always computed:
    `day_of_month_profile` returns a flat distribution when a category has
    no history yet, and `projected_monthly_total` returns zero when there's
    no trailing data — together they produce a sensible-but-quiet forecast
    on day 1 that sharpens as data accumulates.

    All math is in the user's chosen base currency; no intermediate EUR
    pivot. Same-currency transactions need no FX rows at all.
    """
    first, last = _month_bounds(month)
    base_currency = settings_service.get_settings(db).base_currency

    mtd_end = min(today, last)
    actuals = actual_mtd(
        db, user_id=user_id, month=month, through=mtd_end,
        base_currency=base_currency, category_id=category_id,
    )

    has_any_history = forecast_available(db, user_id=user_id, as_of=today)

    # Build per-day forecast contributions for days after today.
    future_per_day: dict[date, Decimal] = {}
    if today < last:
        cat_stmt = select(Category).where(
            Category.user_id == user_id, Category.kind == "expense",
        )
        if category_id is not None:
            cat_stmt = cat_stmt.where(Category.id == category_id)
        for cat in db.execute(cat_stmt).scalars().all():
            projected = projected_monthly_total(
                db, user_id=user_id, category_id=cat.id, as_of=today,
                base_currency=base_currency,
            )
            if projected <= 0:
                continue
            profile = day_of_month_profile(
                db, user_id=user_id, category_id=cat.id, as_of=today,
                base_currency=base_currency,
            )

            remaining_days = list(range(today.day + 1, last.day + 1))
            if not remaining_days:
                continue
            wsum = sum(profile[d - 1] for d in remaining_days)
            if wsum <= 0:
                continue
            for d in remaining_days:
                share = projected * (profile[d - 1] / wsum)
                day_obj = date(first.year, first.month, d)
                future_per_day[day_obj] = (
                    future_per_day.get(day_obj, Decimal(0)) + share
                )

    points: list[DailyPoint] = []
    running = Decimal(0)
    d = first
    while d <= last:
        if d <= mtd_end:
            running = actuals.get(d, running)
            is_fc = False
        else:
            running += future_per_day.get(d, Decimal(0))
            is_fc = True
        cumulative = running.quantize(Decimal("0.01"))
        points.append(DailyPoint(date=d, cumulative=cumulative, is_forecast=is_fc))
        d += timedelta(days=1)

    return DailyCumulativeResponse(
        month=month,
        base_currency=base_currency,
        today=today,
        forecast_available=has_any_history,
        points=points,
    )


# ---------------------------------------------------------------------------
# Step 7 – monthly_buckets composition
# ---------------------------------------------------------------------------

_HORIZON_MONTHS = {"1m": 1, "3m": 3, "6m": 6, "1y": 12, "2y": 24}


def _month_label(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _add_months(label: str, n: int) -> str:
    y, m = (int(p) for p in label.split("-"))
    total = y * 12 + (m - 1) + n
    return f"{total // 12:04d}-{(total % 12) + 1:02d}"


def _split_centered(horizon_months: int) -> tuple[int, int]:
    """Return (past_count, future_count); current month is always 1.
    Total slots = horizon_months. past_count + 1 + future_count == horizon_months."""
    if horizon_months <= 1:
        return (0, 0)
    remaining = horizon_months - 1
    past = remaining // 2
    future = remaining - past
    return (past, future)


def _split_forward(horizon_months: int) -> tuple[int, int]:
    """Forward-only: all future plus the current month."""
    if horizon_months <= 1:
        return (0, 0)
    return (0, horizon_months - 1)


def _monthly_actual_total(
    db: Session, *, user_id: int, month: str, base_currency: str,
    category_id: int | None,
) -> Decimal:
    """Sum expense over a calendar month, expressed in `base_currency`."""
    first, last = _month_bounds(month)
    stmt = (
        select(Transaction)
        .join(Category, Category.id == Transaction.category_id)
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.date >= first,
                Transaction.date <= last,
                Category.kind == "expense",
            )
        )
    )
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    rows = list(db.execute(stmt).scalars().all())

    currencies = {t.currency for t in rows} | {base_currency}
    dates = {t.date for t in rows}
    rates = _load_rates_for(db, currencies, dates)

    total = Decimal(0)
    for t in rows:
        base_amount = _compute_base_amount(
            amount=t.amount,
            currency=t.currency,
            when=t.date,
            base_currency=base_currency,
            rate_for=rates,
        )
        if base_amount is None:
            continue
        total += base_amount
    return total


def _future_month_total(
    db: Session, *, user_id: int, today: date, base_currency: str,
    category_id: int | None,
) -> Decimal:
    """Projected total spend for a single future month in `base_currency` —
    per-category projected monthly totals summed."""
    cat_stmt = select(Category).where(
        Category.user_id == user_id, Category.kind == "expense",
    )
    if category_id is not None:
        cat_stmt = cat_stmt.where(Category.id == category_id)
    total = Decimal(0)
    for cat in db.execute(cat_stmt).scalars().all():
        total += projected_monthly_total(
            db, user_id=user_id, category_id=cat.id, as_of=today,
            base_currency=base_currency,
        )
    return total


def monthly_buckets(
    db: Session,
    *,
    user_id: int,
    horizon: str,
    mode: str,
    today: date,
    category_id: int | None = None,
) -> MonthlyBucketsResponse:
    """One bucket per month over `horizon`. Past months are actual totals;
    future months are forecast totals; current month is split into actual MTD
    + forecast remainder. All totals in the user's chosen base currency; no
    intermediate EUR pivot."""
    if horizon not in _HORIZON_MONTHS:
        raise ValueError(f"unknown horizon: {horizon!r}")
    if mode not in ("centered", "forward"):
        raise ValueError(f"unknown mode: {mode!r}")

    months_count = _HORIZON_MONTHS[horizon]
    past_n, future_n = (
        _split_centered(months_count) if mode == "centered"
        else _split_forward(months_count)
    )

    current_label = _month_label(today)
    labels = (
        [_add_months(current_label, -(past_n - i)) for i in range(past_n)]
        + [current_label]
        + [_add_months(current_label, i + 1) for i in range(future_n)]
    )

    base_currency = settings_service.get_settings(db).base_currency
    has_any_history = forecast_available(db, user_id=user_id, as_of=today)

    points: list[MonthlyPoint] = []
    for label in labels:
        if label < current_label:
            total = _monthly_actual_total(
                db, user_id=user_id, month=label,
                base_currency=base_currency, category_id=category_id,
            )
            points.append(MonthlyPoint(
                month=label,
                total=total.quantize(Decimal("0.01")),
                kind="past",
            ))
        elif label == current_label:
            # Reuse daily_cumulative for the current month so the split is
            # consistent with the daily view.
            daily = daily_cumulative(
                db, user_id=user_id, month=label, today=today,
                category_id=category_id,
            )
            today_pt = next(p for p in daily.points if p.date == today)
            last_pt = daily.points[-1]
            mtd = today_pt.cumulative
            total = last_pt.cumulative
            remainder = (total - mtd).quantize(Decimal("0.01"))
            points.append(MonthlyPoint(
                month=label, total=total, actual_mtd=mtd,
                forecast_remainder=remainder, kind="current",
            ))
        else:
            # Always project — `projected_monthly_total` returns 0 when no
            # history exists, so the bar will be zero-height rather than
            # absent. This keeps the chart shape continuous from day 1.
            future = _future_month_total(
                db, user_id=user_id, today=today,
                base_currency=base_currency, category_id=category_id,
            )
            points.append(MonthlyPoint(
                month=label,
                total=future.quantize(Decimal("0.01")),
                kind="future",
            ))

    return MonthlyBucketsResponse(
        horizon=horizon, mode=mode, base_currency=base_currency,
        today=today, forecast_available=has_any_history, points=points,
    )
