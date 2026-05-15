from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction
from app.services.currencies import SUPPORTED_CURRENCIES
from app.services import settings_service


def _month_bounds(month: str) -> tuple[date, date]:
    """'YYYY-MM' -> (first_day, first_day_of_next_month)."""
    year, mo = map(int, month.split("-"))
    start = date(year, mo, 1)
    end = date(year + (mo // 12), (mo % 12) + 1, 1)
    return start, end


def _ensure_category(db: Session, *, user_id: int, category_id: int) -> Category:
    cat = db.execute(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    ).scalar_one_or_none()
    if cat is None:
        raise LookupError(f"Category {category_id} not found for user {user_id}")
    return cat


_TWO_PLACES = Decimal("0.01")


def _quantize_money(amount: Decimal) -> Decimal:
    return amount.quantize(_TWO_PLACES)


def create_transaction(
    db: Session,
    *,
    user_id: int,
    amount: Decimal,
    tx_date: date,
    category_id: int,
    description: str,
    is_recurring: bool = False,
    currency: str | None = None,
) -> Transaction:
    cat = _ensure_category(db, user_id=user_id, category_id=category_id)
    if cat.kind == "savings":
        if amount == Decimal("0"):
            raise ValueError("amount must be non-zero")
    else:
        if amount <= Decimal("0"):
            raise ValueError("amount must be > 0")

    if currency is None:
        currency = settings_service.get_settings(db).base_currency
    code = currency.upper()
    if code not in SUPPORTED_CURRENCIES:
        raise ValueError(f"unknown currency: {currency!r}")

    tx = Transaction(
        user_id=user_id,
        amount=_quantize_money(amount),
        date=tx_date,
        category_id=category_id,
        description=description,
        is_recurring=is_recurring,
        currency=code,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    if is_recurring:
        # Imported lazily to avoid a circular import.
        from app.services import recurring_service
        recurring_service.create_schedule_for_transaction(db, transaction=tx)

    return tx


def list_transactions(
    db: Session,
    *,
    user_id: int,
    month: str | None = None,
    category_id: int | None = None,
) -> list[Transaction]:
    stmt = select(Transaction).where(Transaction.user_id == user_id)
    if month:
        start, end = _month_bounds(month)
        stmt = stmt.where(Transaction.date >= start, Transaction.date < end)
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    stmt = stmt.order_by(Transaction.date.desc(), Transaction.id.desc())
    return list(db.execute(stmt).scalars().all())


def get_transaction(db: Session, *, user_id: int, transaction_id: int) -> Transaction | None:
    return db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id, Transaction.user_id == user_id
        )
    ).scalar_one_or_none()


def update_transaction(
    db: Session,
    *,
    user_id: int,
    transaction_id: int,
    amount: Decimal | None = None,
    tx_date: date | None = None,
    category_id: int | None = None,
    description: str | None = None,
    currency: str | None = None,
) -> Transaction:
    tx = get_transaction(db, user_id=user_id, transaction_id=transaction_id)
    if tx is None:
        raise LookupError(f"Transaction {transaction_id} not found for user {user_id}")

    if amount is not None or category_id is not None:
        # Validate the effective (post-update) amount against the effective category's kind.
        # This covers three cases:
        #   1. amount only changes  — check new amount vs current category kind
        #   2. category_id only changes — check existing amount vs new category kind
        #   3. both change           — check new amount vs new category kind
        effective_cat_id = category_id if category_id is not None else tx.category_id
        effective_cat = _ensure_category(db, user_id=user_id, category_id=effective_cat_id)
        effective_amount = amount if amount is not None else tx.amount
        if effective_cat.kind == "savings":
            if effective_amount == Decimal("0"):
                raise ValueError("amount must be non-zero")
        else:
            if effective_amount <= Decimal("0"):
                raise ValueError("amount must be > 0")
    if amount is not None:
        tx.amount = _quantize_money(amount)
    if tx_date is not None:
        tx.date = tx_date
    if category_id is not None:
        tx.category_id = category_id
    if description is not None:
        tx.description = description
    if currency is not None:
        code = currency.upper()
        if code not in SUPPORTED_CURRENCIES:
            raise ValueError(f"unknown currency: {currency!r}")
        tx.currency = code

    db.commit()
    db.refresh(tx)
    return tx


def delete_transaction(db: Session, *, user_id: int, transaction_id: int) -> None:
    tx = get_transaction(db, user_id=user_id, transaction_id=transaction_id)
    if tx is None:
        raise LookupError(f"Transaction {transaction_id} not found for user {user_id}")
    db.delete(tx)
    db.commit()
