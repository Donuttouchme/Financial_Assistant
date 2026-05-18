from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class DailyPoint(BaseModel):
    """One day in the daily-cumulative response."""

    date: date
    # Cumulative expense from day 1 of the month through this day.
    # For past + today, this is the actual MTD sum.
    # For future days, this is the projected cumulative spend.
    cumulative: Decimal = Field(..., ge=0)
    # True when this day is strictly after today (i.e., forecast).
    is_forecast: bool


class DailyCumulativeResponse(BaseModel):
    """Daily cumulative MTD + forecast for a single calendar month."""

    month: str  # "YYYY-MM"
    base_currency: str  # 3-letter ISO
    today: date
    # True when the user has any expense activity within the projection
    # lookback window (currently 90 days). False when too thin to project at
    # all — the UI shows an empty-state placeholder instead of a flat line.
    forecast_available: bool
    points: list[DailyPoint]


class MonthlyPoint(BaseModel):
    """One month in the monthly-bucket response."""

    month: str  # "YYYY-MM"
    # Total expense for this month. For the current month this is the
    # *projected* total (MTD-actual + forecast-remainder).
    total: Decimal = Field(..., ge=0)
    # Only populated for the current-month bucket. The split is:
    #   total == actual_mtd + forecast_remainder
    # For purely past or purely future months these are None.
    actual_mtd: Decimal | None = Field(default=None, ge=0)
    forecast_remainder: Decimal | None = Field(default=None, ge=0)
    # Bucket type: "past" | "current" | "future".
    kind: str


class MonthlyBucketsResponse(BaseModel):
    """Per-month buckets across a horizon."""

    horizon: str  # "1m" | "3m" | "6m" | "1y" | "2y"
    mode: str  # "centered" | "forward"
    base_currency: str
    today: date
    forecast_available: bool
    points: list[MonthlyPoint]
