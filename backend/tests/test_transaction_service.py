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


def test_transaction_schedule_id_is_nullable_and_persists(db_session, groceries):
    """schedule_id FK column added in Task D1 must default to None and accept
    a value pointing at a RecurringSchedule row.
    """
    from app.models.recurring_schedule import RecurringSchedule
    from app.models.transaction import Transaction

    # Bare-add: default schedule_id is None.
    tx = transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("1"), tx_date=date(2026, 5, 1),
        category_id=groceries.id, description="parent",
    )
    assert tx.schedule_id is None

    # Seed a schedule and a second tx whose schedule_id points at it.
    sched = RecurringSchedule(
        user_id=1, transaction_id=tx.id, amount=Decimal("1"),
        category_id=groceries.id, description="parent",
        start_date=date(2026, 5, 1), next_occurrence_date=date(2026, 6, 1),
        frequency="monthly",
    )
    db_session.add(sched)
    db_session.flush()

    child = Transaction(
        user_id=1, amount=Decimal("1"), date=date(2026, 6, 1),
        category_id=groceries.id, description="child", schedule_id=sched.id,
    )
    db_session.add(child)
    db_session.flush()

    db_session.refresh(child)
    assert child.schedule_id == sched.id


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


def test_search_matches_description_case_insensitive(db_session):
    from app.models.category import Category
    from app.services import transaction_service as svc

    cat = Category(user_id=1, name="Food", kind="expense")
    db_session.add(cat)
    db_session.commit()
    svc.create_transaction(
        db_session, user_id=1, amount=Decimal("10"),
        tx_date=date(2026, 1, 5), category_id=cat.id,
        description="Lunch at Joe", currency="CHF",
    )
    results = svc.search_transactions(db_session, user_id=1, q="LUNCH")
    assert [t.description for t in results] == ["Lunch at Joe"]


def test_search_matches_accented_text_with_casefold(db_session):
    # SQLite LIKE/lower() would FAIL this (ASCII-only folding); casefold passes.
    from app.models.category import Category
    from app.services import transaction_service as svc

    cat = Category(user_id=1, name="Food", kind="expense")
    db_session.add(cat)
    db_session.commit()
    svc.create_transaction(
        db_session, user_id=1, amount=Decimal("10"),
        tx_date=date(2026, 1, 5), category_id=cat.id,
        description="Étterem belváros", currency="CHF",
    )
    results = svc.search_transactions(db_session, user_id=1, q="ÉTTEREM")
    assert len(results) == 1


def test_search_matches_category_name(db_session):
    from app.models.category import Category
    from app.services import transaction_service as svc

    cat = Category(user_id=1, name="Groceries", kind="expense")
    db_session.add(cat)
    db_session.commit()
    svc.create_transaction(
        db_session, user_id=1, amount=Decimal("10"),
        tx_date=date(2026, 1, 5), category_id=cat.id,
        description="weekly shop", currency="CHF",
    )
    results = svc.search_transactions(db_session, user_id=1, q="grocer")
    assert len(results) == 1


def test_search_ignores_month_and_orders_date_desc(db_session):
    from app.models.category import Category
    from app.services import transaction_service as svc

    cat = Category(user_id=1, name="Shopping", kind="expense")
    db_session.add(cat)
    db_session.commit()
    svc.create_transaction(
        db_session, user_id=1, amount=Decimal("10"),
        tx_date=date(2026, 1, 5), category_id=cat.id,
        description="amazon jan", currency="CHF",
    )
    svc.create_transaction(
        db_session, user_id=1, amount=Decimal("20"),
        tx_date=date(2026, 5, 5), category_id=cat.id,
        description="amazon may", currency="CHF",
    )
    results = svc.search_transactions(db_session, user_id=1, q="amazon")
    assert [t.description for t in results] == ["amazon may", "amazon jan"]


def test_search_short_query_returns_empty(db_session):
    from app.models.category import Category
    from app.services import transaction_service as svc

    cat = Category(user_id=1, name="Food", kind="expense")
    db_session.add(cat)
    db_session.commit()
    svc.create_transaction(
        db_session, user_id=1, amount=Decimal("10"),
        tx_date=date(2026, 1, 5), category_id=cat.id,
        description="ab cd", currency="CHF",
    )
    assert svc.search_transactions(db_session, user_id=1, q="a") == []
    assert svc.search_transactions(db_session, user_id=1, q="  ") == []


def _seed_one(db_session, *, description, name="Food"):
    from app.models.category import Category
    from app.services import transaction_service as svc

    cat = Category(user_id=1, name=name, kind="expense")
    db_session.add(cat)
    db_session.commit()
    svc.create_transaction(
        db_session, user_id=1, amount=Decimal("10"),
        tx_date=date(2026, 1, 5), category_id=cat.id,
        description=description, currency="CHF",
    )


def test_search_multiword_matches_concatenated_text(db_session):
    from app.services import transaction_service as svc

    _seed_one(db_session, description="MediaMarkt purchase")
    results = svc.search_transactions(db_session, user_id=1, q="Media Markt")
    assert len(results) == 1


def test_search_single_word_query_matches_spaced_text(db_session):
    from app.services import transaction_service as svc

    _seed_one(db_session, description="Media Markt")
    results = svc.search_transactions(db_session, user_id=1, q="mediamarkt")
    assert len(results) == 1


def test_search_words_can_be_reordered(db_session):
    from app.services import transaction_service as svc

    _seed_one(db_session, description="MediaMarkt")
    results = svc.search_transactions(db_session, user_id=1, q="Markt Media")
    assert len(results) == 1


def test_search_ignores_punctuation(db_session):
    from app.services import transaction_service as svc

    _seed_one(db_session, description="Spar-Market 2026")
    assert len(svc.search_transactions(db_session, user_id=1, q="spar market")) == 1
    assert len(svc.search_transactions(db_session, user_id=1, q="media.markt")) == 0


def test_search_requires_all_words(db_session):
    from app.services import transaction_service as svc

    _seed_one(db_session, description="MediaMarkt")
    assert svc.search_transactions(db_session, user_id=1, q="Media Aldi") == []


def test_search_word_spans_description_and_category(db_session):
    from app.services import transaction_service as svc

    _seed_one(db_session, description="weekly shop", name="Groceries")
    results = svc.search_transactions(db_session, user_id=1, q="grocer shop")
    assert len(results) == 1


def test_search_word_cannot_span_field_boundary(db_session):
    from app.services import transaction_service as svc

    _seed_one(db_session, description="buy media", name="rket club")
    assert svc.search_transactions(db_session, user_id=1, q="mediarket") == []
