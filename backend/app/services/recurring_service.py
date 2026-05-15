from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recurring_schedule import RecurringSchedule
from app.models.transaction import Transaction


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


def run_due_schedules(db: Session, *, today: date) -> list[Transaction]:
    """For every schedule with next_occurrence_date <= today, materialize a transaction
    and advance next_occurrence_date by one month, repeating until it sits in the future.
    Returns the list of newly created transactions in chronological order."""
    due_schedules = db.execute(
        select(RecurringSchedule).where(RecurringSchedule.next_occurrence_date <= today)
    ).scalars().all()

    created: list[Transaction] = []
    for sched in due_schedules:
        while sched.next_occurrence_date <= today:
            new_tx = Transaction(
                user_id=sched.user_id,
                amount=sched.amount,
                date=sched.next_occurrence_date,
                category_id=sched.category_id,
                description=sched.description,
                is_recurring=False,
                currency=sched.currency,
            )
            db.add(new_tx)
            created.append(new_tx)
            sched.next_occurrence_date = sched.next_occurrence_date + relativedelta(months=1)
    db.commit()
    for tx in created:
        db.refresh(tx)
    created.sort(key=lambda t: (t.date, t.id))
    return created
