from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_month, get_current_user_id
from app.schemas.budget_limit import BudgetRead, BudgetSet, BudgetWithSpending
from app.services import budget_service

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


@router.put("/{category_id}", response_model=BudgetRead)
def set_budget(
    category_id: int,
    payload: BudgetSet,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    current_month: str = Depends(get_current_month),
):
    """Set Groceries=X effective from the current calendar month forward.

    The effective month is server-stamped — not client-provided — so a
    misbehaving client can't silently rewrite past history.
    """
    try:
        return budget_service.set_budget(
            db,
            user_id=user_id,
            category_id=category_id,
            effective_month=current_month,
            monthly_limit=payload.monthly_limit,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("", response_model=list[BudgetWithSpending])
def list_budgets(
    month: str = Query(pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    rows = budget_service.list_budgets_with_spending(db, user_id=user_id, month=month)
    return [
        BudgetWithSpending(
            category_id=r.category_id,
            category_name=r.category_name,
            month=r.month,
            monthly_limit=r.monthly_limit,
            spent=r.spent,
            over_budget=r.over_budget,
            overage=r.overage,
        )
        for r in rows
    ]
