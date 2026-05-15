from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.settings import Settings
from app.services.currencies import SUPPORTED_CURRENCIES

_SINGLETON_ID = 1


def get_settings(db: Session) -> Settings:
    s = db.execute(select(Settings).where(Settings.id == _SINGLETON_ID)).scalar_one_or_none()
    if s is None:
        s = Settings(id=_SINGLETON_ID, base_currency="CHF")
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def set_base_currency(db: Session, new_base: str) -> Settings:
    code = new_base.upper()
    if code not in SUPPORTED_CURRENCIES:
        raise ValueError(f"unknown currency: {new_base!r}")
    s = get_settings(db)
    s.base_currency = code
    db.commit()
    db.refresh(s)
    return s
