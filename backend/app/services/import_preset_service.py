from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.import_preset import ImportPreset


def create_preset(
    db: Session, *, user_id: int, name: str, config: dict[str, Any]
) -> ImportPreset:
    existing = db.execute(
        select(ImportPreset).where(
            ImportPreset.user_id == user_id, ImportPreset.name == name
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError(f"Preset '{name}' already exists")

    p = ImportPreset(user_id=user_id, name=name, config=config)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def list_presets(db: Session, *, user_id: int) -> list[ImportPreset]:
    rows = db.execute(
        select(ImportPreset)
        .where(ImportPreset.user_id == user_id)
        .order_by(ImportPreset.name)
    ).scalars().all()
    return list(rows)


def get_preset(db: Session, *, user_id: int, preset_id: int) -> ImportPreset | None:
    return db.execute(
        select(ImportPreset).where(
            ImportPreset.id == preset_id, ImportPreset.user_id == user_id
        )
    ).scalar_one_or_none()


def update_preset(
    db: Session,
    *,
    user_id: int,
    preset_id: int,
    name: str,
    config: dict[str, Any],
) -> ImportPreset:
    p = get_preset(db, user_id=user_id, preset_id=preset_id)
    if p is None:
        raise LookupError(f"Preset {preset_id} not found")
    p.name = name
    p.config = config
    db.commit()
    db.refresh(p)
    return p


def delete_preset(db: Session, *, user_id: int, preset_id: int) -> None:
    p = get_preset(db, user_id=user_id, preset_id=preset_id)
    if p is None:
        raise LookupError(f"Preset {preset_id} not found")
    db.delete(p)
    db.commit()
