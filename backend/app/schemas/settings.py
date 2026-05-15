from pydantic import BaseModel, ConfigDict, Field


class SettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    base_currency: str


class BaseCurrencyPatch(BaseModel):
    base_currency: str = Field(min_length=3, max_length=3)
