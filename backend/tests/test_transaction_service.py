from datetime import date
from decimal import Decimal

import pytest

from app.services import category_service, transaction_service


@pytest.fixture
def groceries(db_session):
    return category_service.create_category(db_session, user_id=1, name="Groceries")


def test_create_transaction_persists_fields(db_session, groceries):
    tx = transaction_service.create_transaction(
        db_session,
        user_id=1,
        amount=Decimal("12.34"),
        tx_date=date(2026, 5, 10),
        category_id=groceries.id,
        description="Milk",
        is_recurring=False,
    )
    assert tx.id is not None
    assert tx.amount == Decimal("12.34")
    assert tx.date == date(2026, 5, 10)
    assert tx.category_id == groceries.id
    assert tx.description == "Milk"
    assert tx.user_id == 1


def test_create_transaction_rejects_non_positive_amount(db_session, groceries):
    with pytest.raises(ValueError, match="amount"):
        transaction_service.create_transaction(
            db_session,
            user_id=1,
            amount=Decimal("0"),
            tx_date=date(2026, 5, 10),
            category_id=groceries.id,
            description="",
        )


def test_create_transaction_rejects_unknown_category(db_session):
    with pytest.raises(LookupError):
        transaction_service.create_transaction(
            db_session,
            user_id=1,
            amount=Decimal("10"),
            tx_date=date(2026, 5, 10),
            category_id=999,
            description="x",
        )


def test_list_transactions_filters_by_month(db_session, groceries):
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("5"), tx_date=date(2026, 5, 1),
        category_id=groceries.id, description="May 1",
    )
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("5"), tx_date=date(2026, 5, 31),
        category_id=groceries.id, description="May 31",
    )
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("5"), tx_date=date(2026, 6, 1),
        category_id=groceries.id, description="June",
    )

    may = transaction_service.list_transactions(db_session, user_id=1, month="2026-05")
    assert [tx.description for tx in may] == ["May 31", "May 1"]


def test_list_transactions_filters_by_category(db_session, groceries):
    rent = category_service.create_category(db_session, user_id=1, name="Rent")
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("5"), tx_date=date(2026, 5, 1),
        category_id=groceries.id, description="Food",
    )
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500"), tx_date=date(2026, 5, 1),
        category_id=rent.id, description="May rent",
    )

    only_rent = transaction_service.list_transactions(db_session, user_id=1, category_id=rent.id)
    assert [tx.description for tx in only_rent] == ["May rent"]


def test_update_transaction_changes_fields(db_session, groceries):
    tx = transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("5"), tx_date=date(2026, 5, 1),
        category_id=groceries.id, description="Old",
    )

    updated = transaction_service.update_transaction(
        db_session, user_id=1, transaction_id=tx.id,
        amount=Decimal("9.99"), description="New",
    )
    assert updated.amount == Decimal("9.99")
    assert updated.description == "New"
    assert updated.date == date(2026, 5, 1)  # unchanged


def test_delete_transaction_removes_it(db_session, groceries):
    tx = transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("5"), tx_date=date(2026, 5, 1),
        category_id=groceries.id, description="X",
    )
    transaction_service.delete_transaction(db_session, user_id=1, transaction_id=tx.id)
    assert transaction_service.list_transactions(db_session, user_id=1) == []


def test_create_transaction_accepts_negative_amount_for_savings(db_session):
    cat = category_service.create_category(
        db_session, user_id=1, name="Emergency", kind="savings"
    )
    tx = transaction_service.create_transaction(
        db_session,
        user_id=1,
        amount=Decimal("-200.00"),
        tx_date=date(2026, 5, 13),
        category_id=cat.id,
        description="Used for car repair",
    )
    assert tx.amount == Decimal("-200.00")


def test_create_transaction_accepts_positive_amount_for_savings(db_session):
    cat = category_service.create_category(
        db_session, user_id=1, name="Vacation 2027", kind="savings"
    )
    tx = transaction_service.create_transaction(
        db_session,
        user_id=1,
        amount=Decimal("500.00"),
        tx_date=date(2026, 5, 13),
        category_id=cat.id,
        description="May deposit",
    )
    assert tx.amount == Decimal("500.00")


def test_create_transaction_rejects_negative_amount_for_expense(db_session):
    cat = category_service.create_category(
        db_session, user_id=1, name="Groceries Neg", kind="expense"
    )
    with pytest.raises(ValueError, match="must be > 0"):
        transaction_service.create_transaction(
            db_session,
            user_id=1,
            amount=Decimal("-50.00"),
            tx_date=date(2026, 5, 13),
            category_id=cat.id,
            description="bad input",
        )


def test_create_transaction_rejects_zero_amount_for_savings(db_session):
    cat = category_service.create_category(
        db_session, user_id=1, name="Vacation 2028", kind="savings"
    )
    with pytest.raises(ValueError, match="non-zero"):
        transaction_service.create_transaction(
            db_session,
            user_id=1,
            amount=Decimal("0"),
            tx_date=date(2026, 5, 13),
            category_id=cat.id,
            description="zero is meaningless",
        )
