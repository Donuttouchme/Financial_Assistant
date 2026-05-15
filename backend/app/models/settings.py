from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Settings(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    base_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="CHF", server_default="CHF"
    )
