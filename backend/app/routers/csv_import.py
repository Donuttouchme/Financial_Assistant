from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
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


def _mark_duplicates(db: Session, user_id: int, rows: list[ParsedRow]) -> None:
    """In-place: set row.is_duplicate=True when (date, |amount|, description) matches an existing tx."""
    has_valid = any(r.date and r.amount is not None for r in rows)
    if not has_valid:
        return
    existing = db.execute(
        select(Transaction.date, Transaction.amount, Transaction.description).where(
            Transaction.user_id == user_id
        )
    ).all()
    existing_keys = {(d, abs(Decimal(str(a))), desc) for d, a, desc in existing}
    for r in rows:
        if r.date and r.amount is not None:
            if (r.date, abs(r.amount), r.description) in existing_keys:
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

    # Eager-fill FX rates for all unique transaction dates upfront
    unique_dates = {
        r.date
        for sel in payload.selections
        if (r := by_index.get(sel.row_index)) is not None and r.date is not None
    }
    await fx_service.ensure_rates_for_dates(db, unique_dates)

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
