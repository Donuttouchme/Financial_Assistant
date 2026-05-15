from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FxRate(Base):
    __tablename__ = "fx_rates"

    currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    date: Mapped[date_type] = mapped_column(Date, primary_key=True)
    rate_to_eur: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
