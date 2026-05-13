from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ImportPresetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    config: dict[str, Any] = Field(default_factory=dict)


class ImportPresetUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    config: dict[str, Any] = Field(default_factory=dict)


class ImportPresetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime
