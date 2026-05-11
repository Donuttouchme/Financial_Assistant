from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RecurringScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: int
    amount: Decimal
    category_id: int
    description: str
    start_date: date_type
    next_occurrence_date: date_type
    frequency: str
