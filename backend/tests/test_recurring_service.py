from datetime import date
from decimal import Decimal

import pytest
from dateutil.relativedelta import relativedelta

from app.services import category_service, recurring_service, transaction_service


@pytest.fixture
def rent_category(db_session):
    return category_service.create_category(db_session, user_id=1, name="Rent")


def test_create_recurring_transaction_creates_schedule(db_session, rent_category):
    tx = transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500"), tx_date=date(2026, 5, 1),
        category_id=rent_category.id, description="Rent", is_recurring=True,
    )
    schedules = recurring_service.list_schedules(db_session, user_id=1)
    assert len(schedules) == 1
    sched = schedules[0]
    assert sched.transaction_id == tx.id
    assert sched.next_occurrence_date == date(2026, 6, 1)
    assert sched.amount == Decimal("500")
    assert sched.category_id == rent_category.id


def test_non_recurring_transaction_creates_no_schedule(db_session, rent_category):
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("5"), tx_date=date(2026, 5, 1),
        category_id=rent_category.id, description="One-off", is_recurring=False,
    )
    assert recurring_service.list_schedules(db_session, user_id=1) == []


def test_run_due_schedules_creates_transactions_until_future(db_session, rent_category):
    # Seed: schedule with next_occurrence_date in the past (March), today = May 15
    tx = transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500"), tx_date=date(2026, 2, 1),
        category_id=rent_category.id, description="Rent", is_recurring=True,
    )
    sched = recurring_service.list_schedules(db_session, user_id=1)[0]
    assert sched.next_occurrence_date == date(2026, 3, 1)

    created = recurring_service.run_due_schedules(db_session, today=date(2026, 5, 15))

    # March, April, May should have been materialized.
    assert len(created) == 3
    assert [t.date for t in created] == [date(2026, 3, 1), date(2026, 4, 1), date(2026, 5, 1)]
    for new_tx in created:
        assert new_tx.amount == Decimal("500")
        assert new_tx.category_id == rent_category.id
        assert new_tx.is_recurring is False  # generated children are not themselves recurring

    db_session.refresh(sched)
    assert sched.next_occurrence_date == date(2026, 6, 1)

    # Idempotency: rerun on same day generates nothing more.
    again = recurring_service.run_due_schedules(db_session, today=date(2026, 5, 15))
    assert again == []


def test_run_due_schedules_skips_future_only_schedules(db_session, rent_category):
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500"), tx_date=date(2026, 12, 1),
        category_id=rent_category.id, description="Future rent", is_recurring=True,
    )
    created = recurring_service.run_due_schedules(db_session, today=date(2026, 5, 15))
    assert created == []


def test_delete_recurring_transaction_removes_its_schedule(db_session, rent_category):
    tx = transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500"), tx_date=date(2026, 5, 1),
        category_id=rent_category.id, description="Rent", is_recurring=True,
    )
    transaction_service.delete_transaction(db_session, user_id=1, transaction_id=tx.id)
    assert recurring_service.list_schedules(db_session, user_id=1) == []
