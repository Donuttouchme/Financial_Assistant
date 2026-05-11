from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category


def create_category(db: Session, *, user_id: int, name: str) -> Category:
    existing = db.execute(
        select(Category).where(Category.user_id == user_id, Category.name == name)
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError(f"Category '{name}' already exists for user {user_id}")

    cat = Category(user_id=user_id, name=name)
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
    db.delete(cat)
    db.commit()
