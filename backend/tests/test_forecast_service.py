from datetime import date, timedelta
from decimal import Decimal

from app.services import forecast_service, settings_service
from app.models.category import Category
from app.models.transaction import Transaction


def test_actual_mtd_sums_expense_only_in_base_currency(db_session):
    income_cat = Category(name="Salary", kind="income", user_id=1)
    food_cat = Category(name="Food", kind="expense", user_id=1)
    db_session.add_all([income_cat, food_cat])
    db_session.commit()

    db_session.add_all([
        Transaction(user_id=1, category_id=food_cat.id, amount=Decimal("10"),
                    currency="EUR", date=date(2026, 5, 1), description=""),
        Transaction(user_id=1, category_id=food_cat.id, amount=Decimal("15"),
                    currency="EUR", date=date(2026, 5, 3), description=""),
        # Income must NOT count toward expense MTD.
        Transaction(user_id=1, category_id=income_cat.id, amount=Decimal("100"),
                    currency="EUR", date=date(2026, 5, 2), description=""),
    ])
    db_session.commit()

    cum = forecast_service.actual_mtd(
        db_session, user_id=1, month="2026-05", through=date(2026, 5, 3),
        base_currency="EUR",
    )

    # Amounts are EUR, base is EUR; no FX needed; so base_amount == amount.
    assert cum[date(2026, 5, 1)] == Decimal("10")
    assert cum[date(2026, 5, 2)] == Decimal("10")  # no expense day 2; cumulative steady
    assert cum[date(2026, 5, 3)] == Decimal("25")
    assert date(2026, 5, 4) not in cum


def test_actual_mtd_scopes_by_user(db_session):
    food1 = Category(name="Food", kind="expense", user_id=1)
    food2 = Category(name="Food", kind="expense", user_id=2)
    db_session.add_all([food1, food2])
    db_session.commit()

    db_session.add_all([
        Transaction(user_id=1, category_id=food1.id, amount=Decimal("10"),
                    currency="EUR", date=date(2026, 5, 1), description=""),
        Transaction(user_id=2, category_id=food2.id, amount=Decimal("99"),
                    currency="EUR", date=date(2026, 5, 1), description=""),
    ])
    db_session.commit()

    cum = forecast_service.actual_mtd(
        db_session, user_id=1, month="2026-05", through=date(2026, 5, 1),
        base_currency="EUR",
    )
    assert cum[date(2026, 5, 1)] == Decimal("10")  # user 2's tx is invisible


def test_actual_mtd_converts_foreign_currency_to_base(db_session):
    from app.models.fx_rate import FxRate

    food = Category(name="Food", kind="expense", user_id=1)
    db_session.add(food); db_session.commit()

    # rate_to_eur(USD) = 2.0 means "1 EUR = 2 USD" (frankfurter convention).
    # So 10 USD -> EUR = 10 / 2 = 5.00 EUR.
    db_session.add(FxRate(currency="USD", date=date(2026, 5, 1),
                          rate_to_eur=Decimal("2.0")))
    db_session.add(Transaction(user_id=1, category_id=food.id,
                               amount=Decimal("10"), currency="USD",
                               date=date(2026, 5, 1), description=""))
    db_session.commit()

    cum = forecast_service.actual_mtd(
        db_session, user_id=1, month="2026-05", through=date(2026, 5, 1),
        base_currency="EUR",
    )
    assert cum[date(2026, 5, 1)] == Decimal("5.00")  # 10 USD / 2.0


def test_actual_mtd_includes_same_currency_tx_without_fx_row(db_session):
    """Same-currency transactions must NOT require FX coverage.

    Regression for v1.2.1: forecast_service hardcoded an EUR pivot and routed
    every transaction through `_compute_base_amount(..., base_currency=EUR)`.
    For a CHF-base user with CHF transactions, this required `rate(CHF, date)`
    rows that simply don't exist for historical days, so those transactions
    were silently dropped from the forecast (returned None → `continue`). Only
    transactions added on days where the user happened to refresh FX rates
    (typically today) survived — matching the user-reported symptom that "only
    after-update transactions show up".

    Same-currency conversion should never need an FX lookup.
    """
    settings_service.set_base_currency(db_session, "CHF")
    food = Category(name="Food", kind="expense", user_id=1)
    db_session.add(food); db_session.commit()

    db_session.add_all([
        Transaction(user_id=1, category_id=food.id, amount=Decimal("100"),
                    currency="CHF", date=date(2026, 5, 2), description=""),
        Transaction(user_id=1, category_id=food.id, amount=Decimal("50"),
                    currency="CHF", date=date(2026, 5, 3), description=""),
    ])
    db_session.commit()

    # No FxRate rows at all — same-currency conversions must still succeed.
    resp = forecast_service.daily_cumulative(
        db_session, user_id=1, month="2026-05", today=date(2026, 5, 5),
    )
    assert resp.base_currency == "CHF"
    p2 = next(p for p in resp.points if p.date == date(2026, 5, 2))
    p5 = next(p for p in resp.points if p.date == date(2026, 5, 5))
    assert p2.cumulative == Decimal("100.00")
    assert p5.cumulative == Decimal("150.00")


def test_day_of_month_profile_normalizes_to_one(db_session):
    food = Category(name="Food", kind="expense", user_id=1)
    db_session.add(food); db_session.commit()

    # Spread 90 EUR across day 1 (60) and day 15 (30) of trailing month.
    db_session.add_all([
        Transaction(user_id=1, category_id=food.id, amount=Decimal("60"),
                    currency="EUR", date=date(2026, 4, 1), description=""),
        Transaction(user_id=1, category_id=food.id, amount=Decimal("30"),
                    currency="EUR", date=date(2026, 4, 15), description=""),
    ])
    db_session.commit()

    profile = forecast_service.day_of_month_profile(
        db_session, user_id=1, category_id=food.id, as_of=date(2026, 5, 1),
        base_currency="EUR",
    )

    assert len(profile) == 31
    # Day 1 carried 60 of 90, day 15 carried 30 of 90. Smoothing spreads a bit
    # to neighbours but peaks remain.
    assert profile[0] > profile[1] > 0       # day 1 peak
    assert profile[14] > profile[13] > 0     # day 15 peak
    assert profile[14] > profile[15]         # day 15 > day 16
    assert abs(sum(profile) - Decimal("1")) < Decimal("0.001")


def test_day_of_month_profile_flat_when_no_data(db_session):
    food = Category(name="Food", kind="expense", user_id=1)
    db_session.add(food); db_session.commit()

    profile = forecast_service.day_of_month_profile(
        db_session, user_id=1, category_id=food.id, as_of=date(2026, 5, 1),
        base_currency="EUR",
    )

    assert len(profile) == 31
    assert all(abs(p - Decimal("1") / 31) < Decimal("0.001") for p in profile)


def test_day_of_month_profile_ignores_other_users(db_session):
    food1 = Category(name="Food", kind="expense", user_id=1)
    food2 = Category(name="Food", kind="expense", user_id=2)
    db_session.add_all([food1, food2]); db_session.commit()

    db_session.add_all([
        # Only user 2 has data — user 1's profile should be flat.
        Transaction(user_id=2, category_id=food2.id, amount=Decimal("100"),
                    currency="EUR", date=date(2026, 4, 1), description=""),
    ])
    db_session.commit()

    profile = forecast_service.day_of_month_profile(
        db_session, user_id=1, category_id=food1.id, as_of=date(2026, 5, 1),
        base_currency="EUR",
    )
    # No user-1 data → flat.
    assert all(abs(p - Decimal("1") / 31) < Decimal("0.001") for p in profile)


def test_projected_monthly_total_extrapolates_trailing_window(db_session):
    food = Category(name="Food", kind="expense", user_id=1)
    db_session.add(food); db_session.commit()

    # 900 EUR over the past 90 days = 10 EUR/day = 300 EUR/month.
    db_session.add_all([
        Transaction(user_id=1, category_id=food.id, amount=Decimal("10"),
                    currency="EUR",
                    date=date(2026, 5, 1) - timedelta(days=i + 1),
                    description="")
        for i in range(90)
    ])
    db_session.commit()

    total = forecast_service.projected_monthly_total(
        db_session, user_id=1, category_id=food.id, as_of=date(2026, 5, 1),
        base_currency="EUR",
    )

    # 90 * 10 / 90 * 30 = 300, but the trailing window excludes today so we
    # accept a small drift due to month-end boundary effects.
    assert abs(total - Decimal("300")) < Decimal("1")


def test_projected_monthly_total_zero_when_no_history(db_session):
    food = Category(name="Food", kind="expense", user_id=1)
    db_session.add(food); db_session.commit()

    total = forecast_service.projected_monthly_total(
        db_session, user_id=1, category_id=food.id, as_of=date(2026, 5, 1),
        base_currency="EUR",
    )
    assert total == Decimal(0)


def test_projected_monthly_total_scopes_by_user_and_category(db_session):
    food1 = Category(name="Food", kind="expense", user_id=1)
    fuel1 = Category(name="Fuel", kind="expense", user_id=1)
    food2 = Category(name="Food", kind="expense", user_id=2)
    db_session.add_all([food1, fuel1, food2]); db_session.commit()

    db_session.add_all([
        # User 1 / Food: 30 EUR
        Transaction(user_id=1, category_id=food1.id, amount=Decimal("30"),
                    currency="EUR", date=date(2026, 4, 15), description=""),
        # User 1 / Fuel: 100 EUR (must NOT leak into Food projection)
        Transaction(user_id=1, category_id=fuel1.id, amount=Decimal("100"),
                    currency="EUR", date=date(2026, 4, 15), description=""),
        # User 2 / Food: 999 EUR (must NOT leak into user-1 projection)
        Transaction(user_id=2, category_id=food2.id, amount=Decimal("999"),
                    currency="EUR", date=date(2026, 4, 15), description=""),
    ])
    db_session.commit()

    total = forecast_service.projected_monthly_total(
        db_session, user_id=1, category_id=food1.id, as_of=date(2026, 5, 1),
        base_currency="EUR",
    )
    # 30 EUR over 90-day window: rate 30/90 = 1/3 EUR/day * 30 days = 10 EUR/month.
    assert abs(total - Decimal("10")) < Decimal("0.1")


# ---------------------------------------------------------------------------
# Step 6.1 – cold-start helpers
# ---------------------------------------------------------------------------

def test_forecast_available_false_when_no_history(db_session):
    food = Category(name="Food", kind="expense", user_id=1)
    db_session.add(food); db_session.commit()
    # No expense transactions yet.
    assert forecast_service.forecast_available(
        db_session, user_id=1, as_of=date(2026, 5, 1),
    ) is False


def test_forecast_available_true_with_any_history(db_session):
    food = Category(name="Food", kind="expense", user_id=1)
    db_session.add(food); db_session.commit()
    # A single expense day flips the flag — the forecast renders from day 1
    # of usage; quality improves silently as data accumulates.
    db_session.add(Transaction(
        user_id=1, category_id=food.id, amount=Decimal("1"),
        currency="EUR", date=date(2026, 4, 30), description="",
    ))
    db_session.commit()
    assert forecast_service.forecast_available(
        db_session, user_id=1, as_of=date(2026, 5, 1),
    ) is True


def test_forecast_available_ignores_other_users(db_session):
    food = Category(name="Food", kind="expense", user_id=2)
    db_session.add(food); db_session.commit()
    db_session.add(Transaction(
        user_id=2, category_id=food.id, amount=Decimal("1"),
        currency="EUR", date=date(2026, 4, 30), description="",
    ))
    db_session.commit()
    # User 1 has no history of their own.
    assert forecast_service.forecast_available(
        db_session, user_id=1, as_of=date(2026, 5, 1),
    ) is False


# ---------------------------------------------------------------------------
# Step 6.3 – daily_cumulative
# ---------------------------------------------------------------------------

def test_daily_cumulative_basic_shape_in_eur_base(db_session):
    settings_service.set_base_currency(db_session, "EUR")

    today = date(2026, 5, 16)
    food = Category(name="Food", kind="expense", user_id=1)
    db_session.add(food); db_session.commit()

    db_session.add(Transaction(
        user_id=1, category_id=food.id, amount=Decimal("20"),
        currency="EUR", date=date(2026, 5, 5), description="",
    ))
    db_session.commit()

    resp = forecast_service.daily_cumulative(
        db_session, user_id=1, month="2026-05", today=today,
    )

    assert resp.month == "2026-05"
    assert resp.base_currency == "EUR"
    assert resp.today == today
    assert len(resp.points) == 31

    p5 = next(p for p in resp.points if p.date == date(2026, 5, 5))
    assert p5.cumulative == Decimal("20")
    assert p5.is_forecast is False

    p17 = next(p for p in resp.points if p.date == date(2026, 5, 17))
    assert p17.is_forecast is True

    # No history → no forecast → future cumulative = today cumulative.
    today_pt = next(p for p in resp.points if p.date == today)
    assert p17.cumulative == today_pt.cumulative


def test_daily_cumulative_with_sufficient_history(db_session):
    settings_service.set_base_currency(db_session, "EUR")

    today = date(2026, 5, 16)
    food = Category(name="Food", kind="expense", user_id=1)
    db_session.add(food); db_session.commit()

    # 90 days of EUR 5/day = 5/day rate → 150 EUR/month projection.
    db_session.add_all([
        Transaction(user_id=1, category_id=food.id, amount=Decimal("5"),
                    currency="EUR",
                    date=today - timedelta(days=i + 1),
                    description="")
        for i in range(90)
    ])
    db_session.commit()

    resp = forecast_service.daily_cumulative(
        db_session, user_id=1, month="2026-05", today=today,
    )

    assert resp.forecast_available is True
    # Future cumulative must be strictly greater than today's cumulative.
    today_pt = next(p for p in resp.points if p.date == today)
    last_pt = resp.points[-1]
    assert last_pt.is_forecast is True
    assert last_pt.cumulative > today_pt.cumulative


def test_daily_cumulative_category_filter(db_session):
    settings_service.set_base_currency(db_session, "EUR")
    today = date(2026, 5, 16)

    food = Category(name="Food", kind="expense", user_id=1)
    fuel = Category(name="Fuel", kind="expense", user_id=1)
    db_session.add_all([food, fuel]); db_session.commit()

    db_session.add_all([
        Transaction(user_id=1, category_id=food.id, amount=Decimal("10"),
                    currency="EUR", date=date(2026, 5, 1), description=""),
        Transaction(user_id=1, category_id=fuel.id, amount=Decimal("99"),
                    currency="EUR", date=date(2026, 5, 1), description=""),
    ])
    db_session.commit()

    resp = forecast_service.daily_cumulative(
        db_session, user_id=1, month="2026-05", today=today,
        category_id=food.id,
    )
    today_pt = next(p for p in resp.points if p.date == today)
    assert today_pt.cumulative == Decimal("10")  # fuel excluded


# ---------------------------------------------------------------------------
# Step 7 – monthly_buckets
# ---------------------------------------------------------------------------

def test_monthly_buckets_centered_3m(db_session):
    settings_service.set_base_currency(db_session, "EUR")
    today = date(2026, 5, 16)
    food = Category(name="Food", kind="expense", user_id=1)
    db_session.add(food); db_session.commit()

    db_session.add_all([
        Transaction(user_id=1, category_id=food.id, amount=Decimal("100"),
                    currency="EUR", date=date(2026, 3, 10), description=""),
        Transaction(user_id=1, category_id=food.id, amount=Decimal("200"),
                    currency="EUR", date=date(2026, 4, 10), description=""),
        Transaction(user_id=1, category_id=food.id, amount=Decimal("50"),
                    currency="EUR", date=date(2026, 5, 10), description=""),
    ])
    db_session.commit()

    resp = forecast_service.monthly_buckets(
        db_session, user_id=1, horizon="3m", mode="centered", today=today,
    )

    months = [p.month for p in resp.points]
    assert months == ["2026-04", "2026-05", "2026-06"]

    apr = next(p for p in resp.points if p.month == "2026-04")
    assert apr.kind == "past"
    assert apr.total == Decimal("200.00")
    assert apr.actual_mtd is None
    assert apr.forecast_remainder is None

    may = next(p for p in resp.points if p.month == "2026-05")
    assert may.kind == "current"
    assert may.actual_mtd == Decimal("50.00")
    assert may.forecast_remainder is not None
    assert may.total == may.actual_mtd + may.forecast_remainder

    jun = next(p for p in resp.points if p.month == "2026-06")
    assert jun.kind == "future"
    assert jun.actual_mtd is None
    assert jun.forecast_remainder is None


def test_monthly_buckets_forward_mode_skews_future(db_session):
    settings_service.set_base_currency(db_session, "EUR")
    today = date(2026, 5, 16)
    food = Category(name="Food", kind="expense", user_id=1)
    db_session.add(food); db_session.commit()

    resp = forecast_service.monthly_buckets(
        db_session, user_id=1, horizon="6m", mode="forward", today=today,
    )
    months = [p.month for p in resp.points]
    # 6m forward: 0 past + current + 5 future.
    assert months == [
        "2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10",
    ]


def test_monthly_buckets_2y_centered_has_24_points(db_session):
    settings_service.set_base_currency(db_session, "EUR")
    today = date(2026, 5, 16)

    resp = forecast_service.monthly_buckets(
        db_session, user_id=1, horizon="2y", mode="centered", today=today,
    )
    assert len(resp.points) == 24
    # 24 points centered: 11 past + current + 12 future (past = (24-1)//2 = 11).
    current_idx = next(i for i, p in enumerate(resp.points) if p.kind == "current")
    assert current_idx == 11


def test_monthly_buckets_rejects_unknown_horizon(db_session):
    today = date(2026, 5, 16)
    try:
        forecast_service.monthly_buckets(
            db_session, user_id=1, horizon="bogus", mode="centered", today=today,
        )
    except ValueError as e:
        assert "horizon" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_monthly_buckets_category_filter(db_session):
    settings_service.set_base_currency(db_session, "EUR")
    today = date(2026, 5, 16)
    food = Category(name="Food", kind="expense", user_id=1)
    fuel = Category(name="Fuel", kind="expense", user_id=1)
    db_session.add_all([food, fuel]); db_session.commit()

    db_session.add_all([
        Transaction(user_id=1, category_id=food.id, amount=Decimal("20"),
                    currency="EUR", date=date(2026, 4, 1), description=""),
        Transaction(user_id=1, category_id=fuel.id, amount=Decimal("80"),
                    currency="EUR", date=date(2026, 4, 1), description=""),
    ])
    db_session.commit()

    resp = forecast_service.monthly_buckets(
        db_session, user_id=1, horizon="3m", mode="centered", today=today,
        category_id=food.id,
    )
    apr = next(p for p in resp.points if p.month == "2026-04")
    assert apr.total == Decimal("20.00")  # fuel excluded
