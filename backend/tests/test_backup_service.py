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


# --- restore lifecycle (Task E2) ----------------------------------------
#
# These tests cover the export/stage/commit triad. The live DB path is
# redirected via ``monkeypatch`` against ``settings.resolved_db_path`` so the
# real database file is never touched. ``resolved_db_path`` is a *method* on
# the Settings instance, so we replace it with a lambda returning a string.


from app.config import Settings, settings  # noqa: E402  (scoped to E2 tests)


def _redirect_live_db(monkeypatch, tmp_path: Path) -> Path:
    """Point the live DB at ``tmp_path/live.db`` and return that path.

    Pydantic-v2 ``BaseSettings`` instances block setattr on non-field
    attributes, so we patch ``resolved_db_path`` on the *class* — the bound
    method on every ``Settings`` instance (including the module-level
    ``settings`` singleton) is replaced for the duration of the test.
    """
    live = tmp_path / "live.db"
    monkeypatch.setattr(Settings, "resolved_db_path", lambda self: str(live))
    return live


def test_export_db_returns_live_db_bytes(monkeypatch, tmp_path):
    live = _redirect_live_db(monkeypatch, tmp_path)
    payload = b"SQLite format 3\x00arbitrary-bytes-for-export-test"
    live.write_bytes(payload)

    assert backup_service.export_db() == payload


def test_stage_restore_writes_pending_and_validates(monkeypatch, tmp_path):
    live = _redirect_live_db(monkeypatch, tmp_path)
    # Build a valid SQLite DB elsewhere, then read its bytes as the "upload".
    source = tmp_path / "source.db"
    _build_complete_db(source)
    payload = source.read_bytes()

    pending = backup_service.stage_restore(payload)

    expected_pending = live.parent / f"{live.name}.pending"
    assert pending == expected_pending
    assert pending.exists()
    assert pending.read_bytes() == payload


def test_stage_restore_removes_pending_on_validation_failure(monkeypatch, tmp_path):
    live = _redirect_live_db(monkeypatch, tmp_path)
    # Build a DB missing a required table -> validation must reject it.
    bad_source = tmp_path / "bad.db"
    _build_db_missing_table(bad_source, missing="fx_rates")
    payload = bad_source.read_bytes()

    with pytest.raises(ValueError, match="fx_rates"):
        backup_service.stage_restore(payload)

    pending = live.parent / f"{live.name}.pending"
    assert not pending.exists()


def test_commit_restore_archives_live_and_swaps_in_pending(monkeypatch, tmp_path):
    live = _redirect_live_db(monkeypatch, tmp_path)
    old_live_bytes = b"OLD-LIVE-CONTENT"
    new_pending_bytes = b"NEW-PENDING-CONTENT"
    live.write_bytes(old_live_bytes)
    pending = live.parent / f"{live.name}.pending"
    pending.write_bytes(new_pending_bytes)

    archive = backup_service.commit_restore()

    # The returned path is the timestamped pre-restore archive.
    assert archive.exists()
    assert archive.name.startswith(f"{live.name}.pre-restore-")
    assert archive.read_bytes() == old_live_bytes
    # Live now holds what pending used to hold.
    assert live.read_bytes() == new_pending_bytes
    # Pending was moved away (not just copied).
    assert not pending.exists()


def test_commit_restore_raises_when_no_pending(monkeypatch, tmp_path):
    live = _redirect_live_db(monkeypatch, tmp_path)
    live.write_bytes(b"OLD-LIVE-CONTENT")
    # No .pending file alongside.

    with pytest.raises(FileNotFoundError):
        backup_service.commit_restore()


def test_prune_archives_keeps_last_five(monkeypatch, tmp_path):
    live = _redirect_live_db(monkeypatch, tmp_path)
    # Create 8 archive files with lexicographically sortable timestamps.
    stamps = [
        "20260101-000000",
        "20260102-000000",
        "20260103-000000",
        "20260104-000000",
        "20260105-000000",
        "20260106-000000",
        "20260107-000000",
        "20260108-000000",
    ]
    for s in stamps:
        (live.parent / f"{live.name}.pre-restore-{s}").write_bytes(b"x")

    backup_service._prune_archives(live)

    remaining = sorted(p.name for p in live.parent.glob(f"{live.name}.pre-restore-*"))
    assert len(remaining) == 5
    # The five most-recent timestamps should survive.
    expected = sorted(f"{live.name}.pre-restore-{s}" for s in stamps[-5:])
    assert remaining == expected
