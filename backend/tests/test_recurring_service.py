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


def test_run_due_schedules_merges_multiple_schedules_chronologically(db_session, rent_category):
    # Schedule A: starts 2026-02-01 -> next_occurrence_date 2026-03-01.
    # With today = 2026-04-15, schedule A materializes children on 3/1 and 4/1.
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500"), tx_date=date(2026, 2, 1),
        category_id=rent_category.id, description="Rent", is_recurring=True,
    )

    # Schedule B uses a different category and starts 2026-03-01 -> next_occurrence_date 2026-04-01.
    # With today = 2026-04-15, schedule B materializes a single child on 4/1.
    internet_category = category_service.create_category(db_session, user_id=1, name="Internet")
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("60"), tx_date=date(2026, 3, 1),
        category_id=internet_category.id, description="Internet", is_recurring=True,
    )

    created = recurring_service.run_due_schedules(db_session, today=date(2026, 4, 15))

    # 2 children from schedule A (3/1, 4/1) + 1 child from schedule B (4/1) = 3 total, with a same-date tie on 4/1.
    assert len(created) == 3
    assert [t.date for t in created] == sorted(t.date for t in created)
    assert [(t.date, t.id) for t in created] == sorted((t.date, t.id) for t in created)

    same_date_children = [t for t in created if t.date == date(2026, 4, 1)]
    assert len(same_date_children) == 2

    schedules = recurring_service.list_schedules(db_session, user_id=1)
    assert len(schedules) == 2
    for sched in schedules:
        db_session.refresh(sched)
        assert sched.next_occurrence_date > date(2026, 4, 15)


def test_delete_recurring_transaction_removes_its_schedule(db_session, rent_category):
    tx = transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500"), tx_date=date(2026, 5, 1),
        category_id=rent_category.id, description="Rent", is_recurring=True,
    )
    transaction_service.delete_transaction(db_session, user_id=1, transaction_id=tx.id)
    assert recurring_service.list_schedules(db_session, user_id=1) == []


# --------------------------------------------------------------------------- #
# Task D2: schedule_id stamping, Jan-31 drift fix, update/delete/get helpers.
# --------------------------------------------------------------------------- #


def test_run_due_schedules_sets_schedule_id_on_children(db_session, rent_category):
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500"), tx_date=date(2026, 2, 1),
        category_id=rent_category.id, description="Rent", is_recurring=True,
    )
    sched = recurring_service.list_schedules(db_session, user_id=1)[0]

    created = recurring_service.run_due_schedules(db_session, today=date(2026, 5, 15))

    assert len(created) == 3
    for child in created:
        assert child.schedule_id == sched.id


def test_monthly_on_31st_does_not_drift(db_session, rent_category):
    """A schedule whose anchor day is 31 must clamp to last-day-of-month for
    short months yet snap back to 31 in 31-day months — not stick at 28."""
    from app.models.recurring_schedule import RecurringSchedule

    # Manually construct the schedule to bypass create_schedule_for_transaction's
    # next_occurrence_date seeding (it would set 2026-02-28 from a 2026-01-31
    # start, which is correct for the *first* tick but the subsequent advances
    # are what we are testing).
    sched = RecurringSchedule(
        user_id=1,
        transaction_id=None,  # detach from a transaction for this unit test
        amount=Decimal("500"),
        category_id=rent_category.id,
        description="Rent",
        currency="CHF",
        start_date=date(2026, 1, 31),
        next_occurrence_date=date(2026, 1, 31),
        frequency="monthly",
    )
    # transaction_id is NOT NULL on the model; seed a placeholder tx to satisfy it.
    seed_tx = transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500"), tx_date=date(2026, 1, 31),
        category_id=rent_category.id, description="seed", is_recurring=False,
    )
    sched.transaction_id = seed_tx.id
    db_session.add(sched)
    db_session.commit()
    db_session.refresh(sched)

    created = recurring_service.run_due_schedules(db_session, today=date(2026, 5, 31))

    dates = [t.date for t in created]
    # 2026 is not a leap year so February clamps to the 28th.
    assert dates == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
        date(2026, 5, 31),
    ]
    db_session.refresh(sched)
    assert sched.next_occurrence_date == date(2026, 6, 30)


def test_update_schedule_changes_fields_and_only_affects_future_materialisations(
    db_session, rent_category
):
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500"), tx_date=date(2026, 2, 1),
        category_id=rent_category.id, description="Rent", is_recurring=True,
    )
    sched = recurring_service.list_schedules(db_session, user_id=1)[0]

    first_batch = recurring_service.run_due_schedules(db_session, today=date(2026, 3, 15))
    assert len(first_batch) == 1
    assert first_batch[0].amount == Decimal("500")
    first_id = first_batch[0].id

    updated = recurring_service.update_schedule(
        db_session, sched.id, amount=Decimal("600"), description="Rent (raised)"
    )
    assert updated.amount == Decimal("600")
    assert updated.description == "Rent (raised)"

    second_batch = recurring_service.run_due_schedules(db_session, today=date(2026, 5, 15))
    assert len(second_batch) == 2
    for child in second_batch:
        assert child.amount == Decimal("600")
        assert child.description == "Rent (raised)"

    # Earlier materialisation untouched.
    from app.models.transaction import Transaction
    earlier = db_session.get(Transaction, first_id)
    assert earlier.amount == Decimal("500")
    assert earlier.description == "Rent"


def test_delete_schedule_keeps_children_with_schedule_id_set_to_null(
    db_session, rent_category
):
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500"), tx_date=date(2026, 2, 1),
        category_id=rent_category.id, description="Rent", is_recurring=True,
    )
    sched = recurring_service.list_schedules(db_session, user_id=1)[0]
    sched_id = sched.id

    children = recurring_service.run_due_schedules(db_session, today=date(2026, 5, 15))
    assert len(children) == 3
    child_ids = [c.id for c in children]

    recurring_service.delete_schedule(db_session, sched_id)

    from app.models.recurring_schedule import RecurringSchedule
    from app.models.transaction import Transaction
    assert db_session.get(RecurringSchedule, sched_id) is None
    for cid in child_ids:
        child = db_session.get(Transaction, cid)
        assert child is not None
        assert child.schedule_id is None


def test_update_schedule_raises_lookup_for_missing_id(db_session):
    with pytest.raises(LookupError):
        recurring_service.update_schedule(db_session, 99999, amount=Decimal("1"))


def test_delete_schedule_raises_lookup_for_missing_id(db_session):
    with pytest.raises(LookupError):
        recurring_service.delete_schedule(db_session, 99999)


def test_get_schedule_filters_by_user(db_session, rent_category):
    # rent_category belongs to user_id=1; create one schedule for user 2 too.
    cat2 = category_service.create_category(db_session, user_id=2, name="Rent2")
    transaction_service.create_transaction(
        db_session, user_id=2, amount=Decimal("400"), tx_date=date(2026, 4, 1),
        category_id=cat2.id, description="Rent (u2)", is_recurring=True,
    )
    sched_u2 = recurring_service.list_schedules(db_session, user_id=2)[0]

    # User 1 cannot see user 2's schedule.
    assert recurring_service.get_schedule(db_session, schedule_id=sched_u2.id, user_id=1) is None
    fetched = recurring_service.get_schedule(db_session, schedule_id=sched_u2.id, user_id=2)
    assert fetched is not None
    assert fetched.id == sched_u2.id
