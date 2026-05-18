from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.services import export_service

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/csv")
def export_csv(
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    csv_bytes = export_service.export_transactions_csv(db, user_id=user_id, month=month)
    filename_part = month if month else "all"
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="transactions-{filename_part}.csv"'
        },
    )
