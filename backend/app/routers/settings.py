from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.settings import BaseCurrencyPatch, SettingsRead
from app.services import settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsRead)
def read_settings(db: Session = Depends(get_db)):
    return settings_service.get_settings(db)


@router.patch("/base_currency", response_model=SettingsRead)
def update_base_currency(
    payload: BaseCurrencyPatch,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return settings_service.commit_base_currency_change(db, payload.base_currency, user_id)
    except settings_service.FxNotAvailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/base_currency/preview")
def preview_base_currency(
    payload: BaseCurrencyPatch,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return settings_service.preview_base_currency_change(db, payload.base_currency, user_id)
    except settings_service.FxNotAvailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
