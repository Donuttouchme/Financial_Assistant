from decimal import Decimal

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.csv_import import (
    CsvPreviewRequest,
    CsvPreviewResponse,
    ImportCommitRequest,
    ImportCommitResponse,
    ParsedRow,
)
from app.services import csv_import_service, fx_service, settings_service, transaction_service
from app.services.currencies import SUPPORTED_CURRENCIES

router = APIRouter(prefix="/api/import", tags=["import"])


def _signed_amount(stored: Decimal, kind: str) -> Decimal:
    """Recover the SIGNED amount from a stored Transaction row.

    `Transaction.amount` is non-negative for income/expense kinds; the sign is
    carried by the category kind. We invert for expenses so the dedupe key can
    compare against signed CSV-row amounts. Savings rows may store either sign,
    so we trust the stored value directly.
    """
    val = Decimal(str(stored))
    if kind == "expense":
        return -abs(val)
    if kind == "income":
        return abs(val)
    return val  # savings or any other future kind: pass through as-is


def _mark_duplicates(db: Session, user_id: int, rows: list[ParsedRow]) -> None:
    """In-place: set row.is_duplicate=True when (date, signed_amount, description) matches an existing tx.

    Uses signed amounts so a +45.30 income and a -45.30 expense on the same
    date+description are NOT collapsed as duplicates.
    """
    has_valid = any(r.date and r.amount is not None for r in rows)
    if not has_valid:
        return
    existing = db.execute(
        select(
            Transaction.date,
            Transaction.amount,
            Transaction.description,
            Category.kind,
        )
        .join(Category, Category.id == Transaction.category_id)
        .where(Transaction.user_id == user_id)
    ).all()
    existing_keys = {
        (d, _signed_amount(amt, kind), desc) for d, amt, desc, kind in existing
    }
    for r in rows:
        if r.date and r.amount is not None:
            if (r.date, r.amount, r.description) in existing_keys:
                r.is_duplicate = True


@router.post("/preview", response_model=CsvPreviewResponse)
def preview(
    payload: CsvPreviewRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    rows = csv_import_service.parse_csv(payload.file_content, payload.config)
    _mark_duplicates(db, user_id, rows)
    return CsvPreviewResponse(rows=rows)


@router.post("/commit", response_model=ImportCommitResponse)
async def commit(
    payload: ImportCommitRequest,
    response: Response,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    rows = csv_import_service.parse_csv(payload.file_content, payload.config)
    by_index = {r.row_index: r for r in rows}
    imported = 0
    skipped = 0
    selected_indexes = {sel.row_index for sel in payload.selections}

    # Determine currency fallback: explicit default_currency > config default > base currency
    base_currency = settings_service.get_settings(db).base_currency
    fallback = (
        payload.default_currency
        or payload.config.default_currency
        or base_currency
    ).upper()

    # Eager-fill FX rates for all unique transaction dates upfront. Any dates
    # the fetch couldn't fill (offline / frankfurter down / weekend gap) are
    # surfaced to the client via a response header so the UI can show a toast
    # — rows still get inserted with base_amount=None and self-heal on the
    # next FX refresh.
    unique_dates = {
        r.date
        for sel in payload.selections
        if (r := by_index.get(sel.row_index)) is not None and r.date is not None
    }
    missing_fx_dates = await fx_service.ensure_rates_for_dates(db, unique_dates)
    if missing_fx_dates:
        response.headers["X-Fx-Missing-Dates"] = ",".join(
            d.isoformat() for d in missing_fx_dates
        )

    for sel in payload.selections:
        r = by_index.get(sel.row_index)
        if r is None or r.errors or r.amount is None or r.date is None:
            skipped += 1
            continue
        currency = (r.currency or fallback).upper()
        if currency not in SUPPORTED_CURRENCIES:
            skipped += 1
            continue
        try:
            transaction_service.create_transaction(
                db,
                user_id=user_id,
                amount=r.amount,
                tx_date=r.date,
                category_id=sel.category_id,
                description=r.description,
                is_recurring=sel.is_recurring,
                currency=currency,
            )
            imported += 1
        except (ValueError, LookupError):
            skipped += 1

    # Rows that were parsed but NOT selected count as skipped too.
    not_selected_count = sum(1 for r in rows if r.row_index not in selected_indexes)
    skipped += not_selected_count
    return ImportCommitResponse(imported=imported, skipped=skipped)
