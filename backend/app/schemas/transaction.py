from datetime import date as date_type, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    amount: Decimal = Field(gt=Decimal("0"))
    date: date_type
    category_id: int
    description: str = Field(default="", max_length=255)
    is_recurring: bool = False


class TransactionUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=Decimal("0"))
    date: date_type | None = None
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=255)


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    date: date_type
    category_id: int
    description: str
    is_recurring: bool
    created_at: datetime
    updated_at: datetime
