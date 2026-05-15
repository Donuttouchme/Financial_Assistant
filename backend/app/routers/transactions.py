from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.transaction import TransactionCreate, TransactionRead, TransactionUpdate
from app.services import transaction_service

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        tx = transaction_service.create_transaction(
            db,
            user_id=user_id,
            amount=payload.amount,
            tx_date=payload.date,
            category_id=payload.category_id,
            description=payload.description,
            is_recurring=payload.is_recurring,
            currency=payload.currency,
        )
        return transaction_service.enrich_with_base_amount(db, [tx])[0]
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    category_id: int | None = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    txs = transaction_service.list_transactions(
        db, user_id=user_id, month=month, category_id=category_id
    )
    return transaction_service.enrich_with_base_amount(db, txs)


@router.put("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        tx = transaction_service.update_transaction(
            db,
            user_id=user_id,
            transaction_id=transaction_id,
            amount=payload.amount,
            tx_date=payload.date,
            category_id=payload.category_id,
            description=payload.description,
            currency=payload.currency,
        )
        return transaction_service.enrich_with_base_amount(db, [tx])[0]
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        transaction_service.delete_transaction(
            db, user_id=user_id, transaction_id=transaction_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
