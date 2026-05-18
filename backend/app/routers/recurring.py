from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.recurring import RecurringRead, RecurringUpdate
from app.services import recurring_service

router = APIRouter(prefix="/api/recurring", tags=["recurring"])


@router.get("", response_model=list[RecurringRead])
def list_recurring(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return recurring_service.list_schedules(db, user_id=user_id)


@router.get("/{schedule_id}", response_model=RecurringRead)
def get_recurring(
    schedule_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    sched = recurring_service.get_schedule(db, schedule_id=schedule_id, user_id=user_id)
    if not sched:
        raise HTTPException(status_code=404, detail="schedule not found")
    return sched


@router.patch("/{schedule_id}", response_model=RecurringRead)
def update_recurring(
    schedule_id: int,
    payload: RecurringUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    sched = recurring_service.get_schedule(db, schedule_id=schedule_id, user_id=user_id)
    if not sched:
        raise HTTPException(status_code=404, detail="schedule not found")
    return recurring_service.update_schedule(
        db, schedule_id, **payload.model_dump(exclude_none=True),
    )


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring(
    schedule_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    sched = recurring_service.get_schedule(db, schedule_id=schedule_id, user_id=user_id)
    if not sched:
        raise HTTPException(status_code=404, detail="schedule not found")
    recurring_service.delete_schedule(db, schedule_id)
    return None
