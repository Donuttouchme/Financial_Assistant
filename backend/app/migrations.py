"""Lightweight column-add migrations.

We don't use Alembic for this project — the schema additions so far are tiny
nullable columns. This module runs idempotent ALTER TABLE ADD COLUMN statements
on lifespan startup so an existing on-disk SQLite DB (with the wife's real
data) gets upgraded in-place rather than needing a wipe-and-recreate.

Adding a row here adds ONE column. For more complex migrations (renames, type
changes, data backfills) switch to Alembic.
"""
from sqlalchemy import Engine


# (table, column, type_with_null_or_default)
_COLUMN_ADDS: list[tuple[str, str, str]] = [
    ("categories", "target_amount", "NUMERIC(12,2)"),
    ("categories", "target_date", "DATE"),
]


def _existing_columns(conn, table: str) -> set[str]:
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def run_migrations(engine: Engine) -> None:
    with engine.begin() as conn:
        for table, column, ddl in _COLUMN_ADDS:
            if column not in _existing_columns(conn, table):
                conn.exec_driver_sql(
                    f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"
                )
