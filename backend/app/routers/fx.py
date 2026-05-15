from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.fx import FxRefreshResponse, FxStatusRead
from app.services import fx_service

router = APIRouter(prefix="/api/fx", tags=["fx"])


@router.get("/status", response_model=FxStatusRead)
def fx_status(db: Session = Depends(get_db)):
    latest = fx_service.get_latest_date(db)
    return FxStatusRead(
        latest_date=latest,
        source="frankfurter.app",
        is_fresh=(latest is not None and latest >= date.today()),
    )


@router.post("/refresh", response_model=FxRefreshResponse)
async def fx_refresh(db: Session = Depends(get_db)):
    fetched_date, count = await fx_service.refresh_today(db)
    return FxRefreshResponse(
        fetched_date=fetched_date,
        currencies_updated=count,
        ok=fetched_date is not None,
    )
