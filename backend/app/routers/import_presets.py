from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.import_preset import (
    ImportPresetCreate,
    ImportPresetRead,
    ImportPresetUpdate,
)
from app.services import import_preset_service

router = APIRouter(prefix="/api/import-presets", tags=["import-presets"])


@router.get("", response_model=list[ImportPresetRead])
def list_presets(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return import_preset_service.list_presets(db, user_id=user_id)


@router.post("", response_model=ImportPresetRead, status_code=status.HTTP_201_CREATED)
def create_preset(
    payload: ImportPresetCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return import_preset_service.create_preset(
            db, user_id=user_id, name=payload.name, config=payload.config
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{preset_id}", response_model=ImportPresetRead)
def update_preset(
    preset_id: int,
    payload: ImportPresetUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return import_preset_service.update_preset(
            db,
            user_id=user_id,
            preset_id=preset_id,
            name=payload.name,
            config=payload.config,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preset(
    preset_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        import_preset_service.delete_preset(db, user_id=user_id, preset_id=preset_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
