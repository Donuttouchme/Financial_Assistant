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
    # Simulate a legacy DB that predates all column-add migrations.
    # We create the bare minimum tables (without the migrated columns) to verify
    # that run_migrations adds them correctly.
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
        conn.exec_driver_sql(
            """
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount NUMERIC(12,2) NOT NULL,
                date DATE NOT NULL,
                category_id INTEGER NOT NULL,
                description VARCHAR(255) NOT NULL DEFAULT '',
                is_recurring BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE recurring_schedules (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                transaction_id INTEGER NOT NULL UNIQUE,
                amount NUMERIC(12,2) NOT NULL,
                category_id INTEGER NOT NULL,
                description VARCHAR(255) NOT NULL DEFAULT '',
                start_date DATE NOT NULL,
                next_occurrence_date DATE NOT NULL,
                frequency VARCHAR(16) NOT NULL DEFAULT 'monthly'
            )
            """
        )

    assert "target_amount" not in _columns(eng, "categories")
    assert "target_date" not in _columns(eng, "categories")
    assert "currency" not in _columns(eng, "transactions")
    assert "currency" not in _columns(eng, "recurring_schedules")

    run_migrations(eng)
    assert "target_amount" in _columns(eng, "categories")
    assert "target_date" in _columns(eng, "categories")
    assert "currency" in _columns(eng, "transactions")
    assert "currency" in _columns(eng, "recurring_schedules")
