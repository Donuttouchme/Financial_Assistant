"""Tests for ``app.services.backup_service.validate_uploaded_db``.

The validator must reject an uploaded SQLite file that is missing ANY of the
user-data tables the running app needs. A previous implementation listed only
a subset (``users``, ``categories``, ``transactions``) — so a "valid" backup
could pass while missing ``fx_rates``, ``budget_limits``, ``import_presets``
or ``settings``, then crash the app on first read after restore.

Each missing-table test below corresponds to one table the bug-batch plan
flagged as silently-droppable.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.services import backup_service


# Mirrors backup_service._REQUIRED_TABLES; duplicated locally so the tests
# break loudly if either side drifts (the helper builds DBs against this set).
_ALL_REQUIRED_TABLES = (
    "budget_limits",
    "categories",
    "fx_rates",
    "import_presets",
    "recurring_schedules",
    "settings",
    "transactions",
)


def _build_db_missing_table(path: Path, *, missing: str | None) -> None:
    """Create a SQLite file at ``path`` with every required table EXCEPT ``missing``.

    The schemas are intentionally minimal — validation only checks
    ``sqlite_master`` for table names, so a single ``id INTEGER`` column is
    enough to register each table.
    """
    conn = sqlite3.connect(path)
    try:
        for table in _ALL_REQUIRED_TABLES:
            if table == missing:
                continue
            conn.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)")
        conn.commit()
    finally:
        conn.close()


def _build_complete_db(path: Path) -> None:
    """Create a SQLite file with every required table present."""
    _build_db_missing_table(path, missing=None)


# --- happy path ----------------------------------------------------------


def test_validate_accepts_db_with_all_required_tables(tmp_path):
    p = tmp_path / "good.db"
    _build_complete_db(p)
    # Should not raise.
    backup_service.validate_uploaded_db(p)


# --- one test per required table ----------------------------------------


def test_validate_rejects_db_missing_categories(tmp_path):
    p = tmp_path / "bad.db"
    _build_db_missing_table(p, missing="categories")
    with pytest.raises(ValueError, match="categories"):
        backup_service.validate_uploaded_db(p)


def test_validate_rejects_db_missing_transactions(tmp_path):
    p = tmp_path / "bad.db"
    _build_db_missing_table(p, missing="transactions")
    with pytest.raises(ValueError, match="transactions"):
        backup_service.validate_uploaded_db(p)


def test_validate_rejects_db_missing_fx_rates(tmp_path):
    p = tmp_path / "bad.db"
    _build_db_missing_table(p, missing="fx_rates")
    with pytest.raises(ValueError, match="fx_rates"):
        backup_service.validate_uploaded_db(p)


def test_validate_rejects_db_missing_budget_limits(tmp_path):
    p = tmp_path / "bad.db"
    _build_db_missing_table(p, missing="budget_limits")
    with pytest.raises(ValueError, match="budget_limits"):
        backup_service.validate_uploaded_db(p)


def test_validate_rejects_db_missing_import_presets(tmp_path):
    p = tmp_path / "bad.db"
    _build_db_missing_table(p, missing="import_presets")
    with pytest.raises(ValueError, match="import_presets"):
        backup_service.validate_uploaded_db(p)


def test_validate_rejects_db_missing_settings(tmp_path):
    p = tmp_path / "bad.db"
    _build_db_missing_table(p, missing="settings")
    with pytest.raises(ValueError, match="settings"):
        backup_service.validate_uploaded_db(p)


def test_validate_rejects_db_missing_recurring_schedules(tmp_path):
    p = tmp_path / "bad.db"
    _build_db_missing_table(p, missing="recurring_schedules")
    with pytest.raises(ValueError, match="recurring_schedules"):
        backup_service.validate_uploaded_db(p)


# --- non-SQLite / missing-file guards -----------------------------------


def test_validate_rejects_missing_file(tmp_path):
    p = tmp_path / "does-not-exist.db"
    with pytest.raises(ValueError, match="not found"):
        backup_service.validate_uploaded_db(p)


def test_validate_rejects_non_sqlite_file(tmp_path):
    p = tmp_path / "not-a-db.db"
    p.write_bytes(b"this is just some text, not a SQLite file")
    with pytest.raises(ValueError, match="not a SQLite database"):
        backup_service.validate_uploaded_db(p)
