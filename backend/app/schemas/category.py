from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CategoryKind = Literal["income", "expense"]


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: CategoryKind = "expense"


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: CategoryKind
    created_at: datetime
