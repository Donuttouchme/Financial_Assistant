from dataclasses import dataclass
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BudgetSet(BaseModel):
    """PUT /api/budgets/{category_id} request body.

    The server stamps the effective-from month from the request clock; the
    client cannot set it. Keeps the recurring-budget mental model clean.
    """
    monthly_limit: Decimal = Field(ge=Decimal("0"))


class BudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    month: str
    monthly_limit: Decimal


class BudgetWithSpending(BaseModel):
    category_id: int
    category_name: str
    month: str
    monthly_limit: Decimal
    spent: Decimal
    over_budget: bool
    overage: Decimal


@dataclass
class BudgetWithSpendingRow:
    """Service-layer representation (services don't import schemas)."""
    category_id: int
    category_name: str
    month: str
    monthly_limit: Decimal
    spent: Decimal
    over_budget: bool
    overage: Decimal
