from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.forecast import DailyCumulativeResponse, MonthlyBucketsResponse
from app.services import forecast_service

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("/daily-cumulative", response_model=DailyCumulativeResponse)
def daily_cumulative(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    category_id: int | None = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return forecast_service.daily_cumulative(
        db, user_id=user_id, month=month, today=date.today(),
        category_id=category_id,
    )


@router.get("/monthly-buckets", response_model=MonthlyBucketsResponse)
def monthly_buckets(
    horizon: str = Query(..., pattern=r"^(1m|3m|6m|1y|2y)$"),
    mode: str = Query("centered", pattern=r"^(centered|forward)$"),
    category_id: int | None = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return forecast_service.monthly_buckets(
        db, user_id=user_id, horizon=horizon, mode=mode, today=date.today(),
        category_id=category_id,
    )
