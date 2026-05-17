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
