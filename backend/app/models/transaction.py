from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="CHF", server_default="CHF"
    )
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # use_alter=True breaks the transactions <-> recurring_schedules FK cycle
    # so Base.metadata.create_all / drop_all can order DDL correctly. On SQLite
    # the ALTER is a no-op at column-creation time; the constraint still lives
    # in CREATE TABLE for fresh DBs and is enforced at the SQLAlchemy session
    # layer (ondelete=SET NULL) for existing DBs via the migration in
    # app/migrations.py.
    schedule_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "recurring_schedules.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_transactions_schedule_id",
        ),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    category = relationship("Category")
