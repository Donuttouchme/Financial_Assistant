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


def test_update_transaction_accepts_negative_amount_for_savings(db_session):
    cat = category_service.create_category(
        db_session, user_id=1, name="Emergency", kind="savings"
    )
    tx = transaction_service.create_transaction(
        db_session,
        user_id=1,
        amount=Decimal("100.00"),
        tx_date=date(2026, 5, 13),
        category_id=cat.id,
        description="deposit",
    )
    updated = transaction_service.update_transaction(
        db_session, user_id=1, transaction_id=tx.id, amount=Decimal("-50.00")
    )
    assert updated.amount == Decimal("-50.00")


def test_update_transaction_rejects_zero_amount_for_savings(db_session):
    cat = category_service.create_category(
        db_session, user_id=1, name="Emergency2", kind="savings"
    )
    tx = transaction_service.create_transaction(
        db_session,
        user_id=1,
        amount=Decimal("100.00"),
        tx_date=date(2026, 5, 13),
        category_id=cat.id,
        description="deposit",
    )
    with pytest.raises(ValueError, match="non-zero"):
        transaction_service.update_transaction(
            db_session, user_id=1, transaction_id=tx.id, amount=Decimal("0")
        )


def test_update_transaction_validates_against_new_category_kind(db_session):
    """Cross-kind move: expense tx → savings, with negative amount in same call."""
    expense_cat = category_service.create_category(
        db_session, user_id=1, name="Groceries-T4", kind="expense"
    )
    savings_cat = category_service.create_category(
        db_session, user_id=1, name="Vacation-T4", kind="savings"
    )
    tx = transaction_service.create_transaction(
        db_session,
        user_id=1,
        amount=Decimal("50.00"),
        tx_date=date(2026, 5, 13),
        category_id=expense_cat.id,
        description="x",
    )
    updated = transaction_service.update_transaction(
        db_session,
        user_id=1,
        transaction_id=tx.id,
        amount=Decimal("-25.00"),
        category_id=savings_cat.id,
    )
    assert updated.amount == Decimal("-25.00")
    assert updated.category_id == savings_cat.id


def test_create_transaction_persists_currency(db_session):
    from decimal import Decimal
    from datetime import date

    from app.services import transaction_service
    from app.models.category import Category

    cat = Category(user_id=1, name="Groceries", kind="expense")
    db_session.add(cat)
    db_session.commit()

    tx = transaction_service.create_transaction(
        db_session,
        user_id=1,
        amount=Decimal("12.50"),
        tx_date=date(2026, 5, 14),
        category_id=cat.id,
        description="lunch",
        currency="EUR",
    )
    assert tx.currency == "EUR"


def test_create_transaction_defaults_currency_to_base(db_session):
    from decimal import Decimal
    from datetime import date

    from app.services import transaction_service
    from app.models.category import Category
    from app.services import settings_service

    settings_service.set_base_currency(db_session, "HUF")
    cat = Category(user_id=1, name="Groceries", kind="expense")
    db_session.add(cat)
    db_session.commit()

    tx = transaction_service.create_transaction(
        db_session,
        user_id=1,
        amount=Decimal("12.50"),
        tx_date=date(2026, 5, 14),
        category_id=cat.id,
        description="lunch",
        currency=None,
    )
    assert tx.currency == "HUF"


def test_create_transaction_rejects_unknown_currency(db_session):
    from decimal import Decimal
    from datetime import date
    import pytest

    from app.services import transaction_service
    from app.models.category import Category

    cat = Category(user_id=1, name="Groceries", kind="expense")
    db_session.add(cat)
    db_session.commit()

    with pytest.raises(ValueError, match="unknown currency"):
        transaction_service.create_transaction(
            db_session,
            user_id=1,
            amount=Decimal("12.50"),
            tx_date=date(2026, 5, 14),
            category_id=cat.id,
            description="x",
            currency="ZZZ",
        )


def test_update_transaction_reparent_rejects_invalid_existing_amount(db_session):
    """Re-parent: savings tx with negative amount → expense category, no amount change.

    Before the fix this silently succeeded, leaving a negative-amount tx in an
    expense category — violating the invariant.
    """
    savings_cat = category_service.create_category(
        db_session, user_id=1, name="Emergency3", kind="savings"
    )
    expense_cat = category_service.create_category(
        db_session, user_id=1, name="Rent-T4", kind="expense"
    )
    tx = transaction_service.create_transaction(
        db_session,
        user_id=1,
        amount=Decimal("-100.00"),
        tx_date=date(2026, 5, 13),
        category_id=savings_cat.id,
        description="withdraw",
    )
    with pytest.raises(ValueError, match="must be > 0"):
        transaction_service.update_transaction(
            db_session, user_id=1, transaction_id=tx.id, category_id=expense_cat.id
        )


import pytest


@pytest.mark.asyncio
async def test_create_transaction_triggers_eager_fill(db_session, monkeypatch):
    from datetime import date
    from decimal import Decimal

    from app.models.category import Category
    from app.services import transaction_service, fx_service

    called: list[date] = []

    async def stub_ensure(db, when):
        called.append(when)

    monkeypatch.setattr(fx_service, "ensure_rates_for_date", stub_ensure)

    cat = Category(user_id=1, name="Groceries", kind="expense")
    db_session.add(cat)
    db_session.commit()

    await transaction_service.create_transaction_async(
        db_session,
        user_id=1,
        amount=Decimal("100"),
        tx_date=date(2026, 5, 14),
        category_id=cat.id,
        description="x",
        currency="EUR",
    )
    assert called == [date(2026, 5, 14)]


@pytest.mark.asyncio
async def test_update_transaction_currency_only_does_not_eager_fill(db_session, monkeypatch):
    """A currency-only update (no date change) intentionally skips eager fill.

    base_amount will be null on read until the user changes the date or
    refreshes rates manually. This documents that offline-safe behavior so a
    future change to ensure_rates_for_date doesn't silently break it.
    """
    from datetime import date
    from decimal import Decimal

    from app.models.category import Category
    from app.services import transaction_service, fx_service

    called: list[date] = []

    async def stub_ensure(db, when):
        called.append(when)

    monkeypatch.setattr(fx_service, "ensure_rates_for_date", stub_ensure)

    cat = Category(user_id=1, name="Groceries", kind="expense")
    db_session.add(cat)
    db_session.commit()

    tx = transaction_service.create_transaction(
        db_session,
        user_id=1,
        amount=Decimal("100"),
        tx_date=date(2026, 5, 14),
        category_id=cat.id,
        description="x",
        currency="EUR",
    )

    await transaction_service.update_transaction_async(
        db_session,
        user_id=1,
        transaction_id=tx.id,
        currency="USD",
    )
    assert called == []  # no fetch because tx_date was not changed
