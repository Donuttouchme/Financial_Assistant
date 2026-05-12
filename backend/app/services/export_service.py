import csv
import io

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction
from app.services.transaction_service import _month_bounds


def export_transactions_csv(db: Session, *, user_id: int, month: str | None = None) -> str:
    stmt = (
        select(Transaction, Category.name)
        .join(Category, Category.id == Transaction.category_id)
        .where(Transaction.user_id == user_id)
    )
    if month:
        start, end = _month_bounds(month)
        stmt = stmt.where(Transaction.date >= start, Transaction.date < end)
    stmt = stmt.order_by(Transaction.date.desc(), Transaction.id.desc())

    rows = db.execute(stmt).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "category", "description", "amount"])
    for tx, cat_name in rows:
        writer.writerow([
            tx.date.isoformat(),
            cat_name,
            tx.description,
            f"{tx.amount:.2f}",
        ])
    return buf.getvalue()
