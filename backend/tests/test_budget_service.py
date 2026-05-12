from datetime import date
from decimal import Decimal

import pytest

from app.services import budget_service, category_service, transaction_service


@pytest.fixture
def groceries(db_session):
    return category_service.create_category(db_session, user_id=1, name="Groceries")


def test_set_budget_creates_record(db_session, groceries):
    b = budget_service.set_budget(
        db_session, user_id=1, category_id=groceries.id,
        month="2026-05", monthly_limit=Decimal("200"),
    )
    assert b.id is not None
    assert b.monthly_limit == Decimal("200")
    assert b.month == "2026-05"


def test_set_budget_updates_existing(db_session, groceries):
    budget_service.set_budget(
        db_session, user_id=1, category_id=groceries.id,
        month="2026-05", monthly_limit=Decimal("200"),
    )
    updated = budget_service.set_budget(
        db_session, user_id=1, category_id=groceries.id,
        month="2026-05", monthly_limit=Decimal("250"),
    )
    assert updated.monthly_limit == Decimal("250")

    all_budgets = budget_service.list_budgets_with_spending(
        db_session, user_id=1, month="2026-05"
    )
    assert len(all_budgets) == 1


def test_set_budget_rejects_unknown_category(db_session):
    with pytest.raises(LookupError):
        budget_service.set_budget(
            db_session, user_id=1, category_id=999,
            month="2026-05", monthly_limit=Decimal("10"),
        )


def test_set_budget_rejects_bad_month_format(db_session, groceries):
    with pytest.raises(ValueError, match="month"):
        budget_service.set_budget(
            db_session, user_id=1, category_id=groceries.id,
            month="2026/05", monthly_limit=Decimal("10"),
        )


def test_list_budgets_includes_spent_and_overage(db_session, groceries):
    budget_service.set_budget(
        db_session, user_id=1, category_id=groceries.id,
        month="2026-05", monthly_limit=Decimal("100"),
    )
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("60"), tx_date=date(2026, 5, 3),
        category_id=groceries.id, description="Food",
    )
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("70"), tx_date=date(2026, 5, 10),
        category_id=groceries.id, description="More food",
    )

    rows = budget_service.list_budgets_with_spending(db_session, user_id=1, month="2026-05")
    assert len(rows) == 1
    assert rows[0].category_id == groceries.id
    assert rows[0].monthly_limit == Decimal("100")
    assert rows[0].spent == Decimal("130")
    assert rows[0].over_budget is True
    assert rows[0].overage == Decimal("30")


def test_list_budgets_excludes_transactions_outside_month(db_session, groceries):
    budget_service.set_budget(
        db_session, user_id=1, category_id=groceries.id,
        month="2026-05", monthly_limit=Decimal("100"),
    )
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("999"), tx_date=date(2026, 4, 30),
        category_id=groceries.id, description="April",
    )
    rows = budget_service.list_budgets_with_spending(db_session, user_id=1, month="2026-05")
    assert rows[0].spent == Decimal("0")
    assert rows[0].over_budget is False
    assert rows[0].overage == Decimal("0")


def test_set_budget_rejects_income_category(db_session):
    salary = category_service.create_category(
        db_session, user_id=1, name="Salary", kind="income"
    )
    with pytest.raises(ValueError, match="expense"):
        budget_service.set_budget(
            db_session, user_id=1, category_id=salary.id,
            month="2026-05", monthly_limit=Decimal("1000"),
        )
