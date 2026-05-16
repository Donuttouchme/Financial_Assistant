import csv
import io

from sqlalchemy.orm import Session

from app.services import settings_service, transaction_service


def export_transactions_csv(db: Session, *, user_id: int, month: str | None = None) -> str:
    txs = transaction_service.list_transactions(db, user_id=user_id, month=month)
    enriched = transaction_service.enrich_with_base_amount(db, txs)
    base_currency = settings_service.get_settings(db).base_currency

    # Build a category-id → name lookup from the already-loaded transactions
    from sqlalchemy import select
    from app.models.category import Category
    cat_names = {
        c.id: c.name
        for c in db.execute(
            select(Category).where(Category.user_id == user_id)
        ).scalars().all()
    }

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "amount", "currency", "category", "description", "base_amount", "base_currency"])
    for row in enriched:
        writer.writerow([
            row["date"].isoformat(),
            f"{row['amount']:.2f}",
            row["currency"],
            cat_names.get(row["category_id"], f"#{row['category_id']}"),
            row["description"],
            str(row["base_amount"]) if row["base_amount"] is not None else "",
            base_currency,
        ])
    return buf.getvalue()
