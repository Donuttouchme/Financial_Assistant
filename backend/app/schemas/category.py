from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CategoryKind = Literal["income", "expense", "savings"]


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: CategoryKind = "expense"
    target_amount: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_date: date | None = None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: CategoryKind
    target_amount: Decimal | None = None
    target_date: date | None = None
    created_at: datetime
