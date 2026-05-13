from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
import app.models  # noqa: F401
from app.migrations import run_migrations


def _engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


def _columns(eng, table: str) -> list[str]:
    with eng.begin() as conn:
        return [r[1] for r in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()]


def test_run_migrations_is_idempotent(tmp_path):
    eng = _engine()
    run_migrations(eng)
    run_migrations(eng)  # second call must not raise
    cols = _columns(eng, "categories")
    assert "target_amount" in cols
    assert "target_date" in cols


def test_run_migrations_adds_missing_column_on_legacy_db():
    # Simulate a pre-Task-2 legacy DB by creating the categories table without
    # target_amount / target_date (the columns Task 1's migration runner adds).
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with eng.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name VARCHAR(80) NOT NULL,
                kind VARCHAR(16) NOT NULL DEFAULT 'expense',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_user_category_name UNIQUE (user_id, name)
            )
            """
        )

    assert "target_amount" not in _columns(eng, "categories")
    assert "target_date" not in _columns(eng, "categories")

    run_migrations(eng)
    assert "target_amount" in _columns(eng, "categories")
    assert "target_date" in _columns(eng, "categories")
