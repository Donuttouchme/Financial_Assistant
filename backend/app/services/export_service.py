import csv
import io

from sqlalchemy.orm import Session

from app.services import settings_service, transaction_service


# Cell values starting with these characters are interpreted as formulas by
# Excel/LibreOffice and can execute arbitrary commands (CVE-class: CSV
# injection / formula injection). Prefix offending cells with a single quote
# to neutralise.
_INJECTION_PREFIXES = ("=", "+", "-", "@")

# UTF-8 BOM — Excel on Windows opens CSV as ANSI by default, mojibaking
# non-ASCII characters ("Zürich" → "Z├╝rich"). The BOM forces UTF-8.
_UTF8_BOM = b"\xef\xbb\xbf"


def _safe(cell) -> str:
    """Return cell coerced to str, with formula-injection prefixes neutralised."""
    s = "" if cell is None else str(cell)
    if s and s[0] in _INJECTION_PREFIXES:
        return "'" + s
    return s


def export_transactions_csv(db: Session, *, user_id: int, month: str | None = None) -> bytes:
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
            _safe(row["date"].isoformat()),
            _safe(f"{row['amount']:.2f}"),
            _safe(row["currency"]),
            _safe(cat_names.get(row["category_id"], f"#{row['category_id']}")),
            _safe(row["description"]),
            _safe(str(row["base_amount"]) if row["base_amount"] is not None else ""),
            _safe(base_currency),
        ])
    return _UTF8_BOM + buf.getvalue().encode("utf-8")
