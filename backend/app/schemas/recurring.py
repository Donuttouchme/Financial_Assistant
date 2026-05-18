from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RecurringRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: int
    amount: Decimal
    category_id: int
    description: str
    currency: str
    start_date: date_type
    next_occurrence_date: date_type
    frequency: str


class RecurringUpdate(BaseModel):
    amount: Decimal | None = None
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=255)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    frequency: str | None = Field(default=None, max_length=16)
