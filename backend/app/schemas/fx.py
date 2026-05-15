from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel


class FxStatusRead(BaseModel):
    latest_date: date_type | None
    source: str = "frankfurter.app"
    is_fresh: bool  # True if latest_date == today (or last business day)


class FxRefreshResponse(BaseModel):
    fetched_date: date_type | None
    currencies_updated: int
    ok: bool
