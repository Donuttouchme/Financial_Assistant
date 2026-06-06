"""Service-level tests for the recurring-budget lookup semantics introduced in v1.3.3.

These tests bypass the router so they can plant rows with arbitrary
effective_month values directly in the DB, simulating a multi-month
edit history without juggling the clock dependency.
"""
from decimal import Decimal

import pytest

from app.models.budget_limit import BudgetLimit
from app.models.category import Category
from app.services import budget_service, settings_service


@pytest.fixture
def groceries_cat(db_session):
    cat = Category(user_id=1, name="Groceries", kind="expense")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


def _plant(db, *, cat_id: int, effective_month: str, limit: str) -> None:
    db.add(
        BudgetLimit(
            user_id=1,
            category_id=cat_id,
            month=effective_month,
            monthly_limit=Decimal(limit),
        )
    )
    db.commit()


def test_later_month_returns_most_recent_at_or_before(db_session, groceries_cat):
    settings_service.set_base_currency(db_session, "EUR")
    _plant(db_session, cat_id=groceries_cat.id, effective_month="2026-05", limit="500")
    _plant(db_session, cat_id=groceries_cat.id, effective_month="2026-09", limit="600")

    # May: only the 500 row is effective.
    rows = budget_service.list_budgets_with_spending(
        db_session, user_id=1, month="2026-05"
    )
    assert len(rows) == 1
    assert rows[0].monthly_limit == Decimal("500.00")

    # June, July, August: still 500 (the Sep row hasn't kicked in).
    for m in ("2026-06", "2026-07", "2026-08"):
        rows = budget_service.list_budgets_with_spending(
            db_session, user_id=1, month=m
        )
        assert len(rows) == 1, m
        assert rows[0].monthly_limit == Decimal("500.00"), m

    # September onward: 600.
    for m in ("2026-09", "2026-10", "2027-03"):
        rows = budget_service.list_budgets_with_spending(
            db_session, user_id=1, month=m
        )
        assert len(rows) == 1, m
        assert rows[0].monthly_limit == Decimal("600.00"), m


def test_month_before_any_effective_row_returns_no_row(db_session, groceries_cat):
    settings_service.set_base_currency(db_session, "EUR")
    _plant(db_session, cat_id=groceries_cat.id, effective_month="2026-06", limit="500")

    rows = budget_service.list_budgets_with_spending(
        db_session, user_id=1, month="2026-03"
    )
    assert rows == []


def test_distinct_categories_have_independent_timelines(db_session):
    settings_service.set_base_currency(db_session, "EUR")
    grok = Category(user_id=1, name="Groceries", kind="expense")
    rent = Category(user_id=1, name="Rent", kind="expense")
    db_session.add_all([grok, rent])
    db_session.commit()

    _plant(db_session, cat_id=grok.id, effective_month="2026-01", limit="500")
    _plant(db_session, cat_id=rent.id, effective_month="2026-06", limit="1200")

    rows = budget_service.list_budgets_with_spending(
        db_session, user_id=1, month="2026-03"
    )
    # Only Groceries is effective in March.
    assert len(rows) == 1
    assert rows[0].category_name == "Groceries"

    rows = budget_service.list_budgets_with_spending(
        db_session, user_id=1, month="2026-07"
    )
    by_name = {r.category_name: r for r in rows}
    assert by_name["Groceries"].monthly_limit == Decimal("500.00")
    assert by_name["Rent"].monthly_limit == Decimal("1200.00")


def test_spending_against_recurring_limit(db_session, groceries_cat):
    """Spending is summed for the queried month; limit comes from the most
    recent effective row. Confirms FX-and-aggregation path still works."""
    from datetime import date as _d

    from app.models.transaction import Transaction

    settings_service.set_base_currency(db_session, "EUR")
    _plant(db_session, cat_id=groceries_cat.id, effective_month="2026-01", limit="100")

    db_session.add_all([
        Transaction(
            user_id=1,
            amount=Decimal("60"),
            currency="EUR",
            date=_d(2026, 5, 3),
            category_id=groceries_cat.id,
            description="food",
            is_recurring=False,
        ),
        Transaction(
            user_id=1,
            amount=Decimal("70"),
            currency="EUR",
            date=_d(2026, 5, 10),
            category_id=groceries_cat.id,
            description="more food",
            is_recurring=False,
        ),
    ])
    db_session.commit()

    rows = budget_service.list_budgets_with_spending(
        db_session, user_id=1, month="2026-05"
    )
    assert len(rows) == 1
    assert rows[0].spent == Decimal("130.00")
    assert rows[0].monthly_limit == Decimal("100.00")
    assert rows[0].over_budget is True
    assert rows[0].overage == Decimal("30.00")
