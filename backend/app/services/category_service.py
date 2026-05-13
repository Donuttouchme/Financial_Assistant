from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category

_VALID_KINDS = ("income", "expense", "savings")


def create_category(
    db: Session,
    *,
    user_id: int,
    name: str,
    kind: str = "expense",
    target_amount: Decimal | None = None,
    target_date: date | None = None,
) -> Category:
    if kind not in _VALID_KINDS:
        raise ValueError(f"kind must be one of {_VALID_KINDS}, got {kind!r}")

    if (target_amount is not None or target_date is not None) and kind != "savings":
        raise ValueError(
            "target_amount / target_date only allowed on savings categories"
        )

    existing = db.execute(
        select(Category).where(Category.user_id == user_id, Category.name == name)
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError(f"Category '{name}' already exists for user {user_id}")

    cat = Category(
        user_id=user_id,
        name=name,
        kind=kind,
        target_amount=target_amount,
        target_date=target_date,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def list_categories(db: Session, *, user_id: int) -> list[Category]:
    rows = db.execute(
        select(Category).where(Category.user_id == user_id).order_by(Category.name)
    ).scalars().all()
    return list(rows)


def get_category(db: Session, *, user_id: int, category_id: int) -> Category | None:
    return db.execute(
        select(Category).where(Category.user_id == user_id, Category.id == category_id)
    ).scalar_one_or_none()


def delete_category(db: Session, *, user_id: int, category_id: int) -> None:
    cat = get_category(db, user_id=user_id, category_id=category_id)
    if cat is None:
        raise LookupError(f"Category {category_id} not found for user {user_id}")

    from app.models.transaction import Transaction
    in_use = db.execute(
        select(Transaction.id).where(
            Transaction.user_id == user_id, Transaction.category_id == category_id
        ).limit(1)
    ).scalar_one_or_none()
    if in_use is not None:
        raise PermissionError(f"Category {category_id} is in use by transactions")

    db.delete(cat)
    db.commit()
