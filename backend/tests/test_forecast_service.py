from datetime import date
from decimal import Decimal

from app.services import forecast_service
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
    )

    # Base currency defaults to EUR in tests; amounts are EUR; so base_amount == amount.
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
    )
    assert cum[date(2026, 5, 1)] == Decimal("10")  # user 2's tx is invisible


def test_actual_mtd_converts_foreign_currency_to_base(db_session):
    from app.models.fx_rate import FxRate

    food = Category(name="Food", kind="expense", user_id=1)
    db_session.add(food); db_session.commit()

    # Default base is EUR. Add a USD rate so 10 USD = 9 EUR on this date.
    db_session.add(FxRate(currency="USD", date=date(2026, 5, 1),
                          rate_to_eur=Decimal("0.9")))
    db_session.add(Transaction(user_id=1, category_id=food.id,
                               amount=Decimal("10"), currency="USD",
                               date=date(2026, 5, 1), description=""))
    db_session.commit()

    cum = forecast_service.actual_mtd(
        db_session, user_id=1, month="2026-05", through=date(2026, 5, 1),
    )
    assert cum[date(2026, 5, 1)] == Decimal("9.00")  # 10 USD × 0.9


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
    )
    # No user-1 data → flat.
    assert all(abs(p - Decimal("1") / 31) < Decimal("0.001") for p in profile)
