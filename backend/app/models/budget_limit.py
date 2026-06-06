from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BudgetLimit(Base):
    """Per-category monthly spending limit, applied as a recurring rule.

    The ``month`` column is the **effective-from** month for this limit:
    the limit applies to that month and every later month until a row for
    the same ``(user_id, category_id)`` with a later ``month`` supersedes
    it. Lookup: pick the row with the largest ``month`` value at-or-before
    the queried month.

    Example: a row with month='2026-06', monthly_limit=500 means "Groceries
    is 500 from June 2026 onward." Adding a row month='2026-09',
    monthly_limit=600 changes the effective limit to 600 for Sep 2026+;
    Jun/Jul/Aug still resolve to 500.
    """

    __tablename__ = "budget_limits"
    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "month", name="uq_budget_user_cat_month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # effective-from YYYY-MM
    monthly_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
