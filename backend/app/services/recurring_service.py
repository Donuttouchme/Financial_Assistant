import calendar
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import select, update as sql_update
from sqlalchemy.orm import Session

from app.models.recurring_schedule import RecurringSchedule
from app.models.transaction import Transaction


def _advance_monthly(current: date, anchor_day: int) -> date:
    """Advance one month while honouring the original anchor day.

    The naïve ``current + relativedelta(months=1)`` drifts when the anchor day
    exceeds the destination month's length: from Jan 31 it lands on Feb 28
    and then *sticks* at the 28th for every subsequent month. We instead
    clamp the anchor day to the destination month's last day.
    """
    nxt = current + relativedelta(months=1)
    last_dom = calendar.monthrange(nxt.year, nxt.month)[1]
    return nxt.replace(day=min(anchor_day, last_dom))


def create_schedule_for_transaction(db: Session, *, transaction: Transaction) -> RecurringSchedule:
    sched = RecurringSchedule(
        user_id=transaction.user_id,
        transaction_id=transaction.id,
        amount=transaction.amount,
        category_id=transaction.category_id,
        description=transaction.description,
        currency=transaction.currency,
        start_date=transaction.date,
        next_occurrence_date=transaction.date + relativedelta(months=1),
        frequency="monthly",
    )
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return sched


def list_schedules(db: Session, *, user_id: int) -> list[RecurringSchedule]:
    return list(
        db.execute(
            select(RecurringSchedule).where(RecurringSchedule.user_id == user_id)
        ).scalars().all()
    )


def get_schedule(
    db: Session, *, schedule_id: int, user_id: int
) -> RecurringSchedule | None:
    return db.execute(
        select(RecurringSchedule).where(
            RecurringSchedule.id == schedule_id,
            RecurringSchedule.user_id == user_id,
        )
    ).scalar_one_or_none()


def update_schedule(
    db: Session,
    schedule_id: int,
    *,
    amount=None,
    category_id=None,
    description=None,
    currency=None,
    frequency=None,
) -> RecurringSchedule:
    sched = db.get(RecurringSchedule, schedule_id)
    if not sched:
        raise LookupError(f"schedule {schedule_id} not found")
    if amount is not None:
        sched.amount = amount
    if category_id is not None:
        sched.category_id = category_id
    if description is not None:
        sched.description = description
    if currency is not None:
        sched.currency = currency
    if frequency is not None:
        sched.frequency = frequency
    db.commit()
    db.refresh(sched)
    return sched


def delete_schedule(db: Session, schedule_id: int) -> None:
    """Delete a schedule, detaching any already-materialised children.

    Children rows live in `transactions` with `schedule_id` pointing back at us.
    The FK is declared `ondelete=SET NULL` (model-level and migration-applied),
    but we null them out explicitly so the behaviour holds even when running
    against an existing SQLite DB where the constraint isn't enforced.
    """
    sched = db.get(RecurringSchedule, schedule_id)
    if not sched:
        raise LookupError(f"schedule {schedule_id} not found")
    db.execute(
        sql_update(Transaction)
        .where(Transaction.schedule_id == schedule_id)
        .values(schedule_id=None)
    )
    db.delete(sched)
    db.commit()


def run_due_schedules(db: Session, *, today: date) -> list[Transaction]:
    """For every schedule with next_occurrence_date <= today, materialize a transaction
    and advance next_occurrence_date by one month, repeating until it sits in the future.
    Returns the list of newly created transactions in chronological order."""
    due_schedules = db.execute(
        select(RecurringSchedule).where(RecurringSchedule.next_occurrence_date <= today)
    ).scalars().all()

    created: list[Transaction] = []
    for sched in due_schedules:
        anchor_day = sched.start_date.day
        while sched.next_occurrence_date <= today:
            new_tx = Transaction(
                user_id=sched.user_id,
                amount=sched.amount,
                date=sched.next_occurrence_date,
                category_id=sched.category_id,
                description=sched.description,
                is_recurring=False,
                currency=sched.currency,
                schedule_id=sched.id,
            )
            db.add(new_tx)
            created.append(new_tx)
            sched.next_occurrence_date = _advance_monthly(
                sched.next_occurrence_date, anchor_day
            )
    db.commit()
    for tx in created:
        db.refresh(tx)
    created.sort(key=lambda t: (t.date, t.id))
    return created
