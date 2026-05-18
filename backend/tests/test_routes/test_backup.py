"""End-to-end tests for the /api/backup router.

Download returns the live DB file as an octet-stream attachment. Restore
stages + commits an uploaded SQLite DB and schedules an exit(75) so the
launcher's RUN.bat loop relaunches uvicorn — these tests intercept the
threaded exit so the test process doesn't actually die.

The live DB path is monkey-patched onto a tmp_path so the real database is
never touched, mirroring the pattern in test_backup_service.py.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path

import pytest

from app.config import Settings


_ALL_REQUIRED_TABLES = (
    "budget_limits",
    "categories",
    "fx_rates",
    "import_presets",
    "recurring_schedules",
    "settings",
    "transactions",
)


def _build_complete_db_bytes(tmp_path: Path) -> bytes:
    """Create a fresh SQLite file with every required table and return its bytes."""
    p = tmp_path / "_source_for_upload.db"
    conn = sqlite3.connect(p)
    try:
        for table in _ALL_REQUIRED_TABLES:
            conn.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)")
        conn.commit()
    finally:
        conn.close()
    return p.read_bytes()


def _redirect_live_db(monkeypatch, tmp_path: Path) -> Path:
    """Patch the live DB path so tests never touch the real file. Pydantic-v2
    BaseSettings blocks setattr on non-fields, so we patch on the class."""
    live = tmp_path / "live.db"
    monkeypatch.setattr(Settings, "resolved_db_path", lambda self: str(live))
    return live


def test_download_returns_sqlite_attachment(client, monkeypatch, tmp_path):
    live = _redirect_live_db(monkeypatch, tmp_path)
    # Seed the live DB with a real (minimal) SQLite file so the magic bytes match.
    conn = sqlite3.connect(live)
    conn.execute("CREATE TABLE dummy (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

    res = client.get("/api/backup/download")

    assert res.status_code == 200
    assert res.headers["content-type"] == "application/octet-stream"
    assert "attachment" in res.headers["content-disposition"]
    assert "financial.db" in res.headers["content-disposition"]
    assert res.content[:16] == b"SQLite format 3\x00"


def test_restore_with_invalid_db_returns_400(client, monkeypatch, tmp_path):
    live = _redirect_live_db(monkeypatch, tmp_path)
    # Seed a live DB so export_db won't fail in unrelated tests; not relevant here.
    live.write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)

    res = client.post(
        "/api/backup/restore",
        files={"file": ("backup.db", b"this is not a sqlite file", "application/octet-stream")},
    )

    assert res.status_code == 400


def test_restore_with_valid_db_schedules_exit_75(client, monkeypatch, tmp_path):
    live = _redirect_live_db(monkeypatch, tmp_path)
    # Seed live DB and prepare valid upload bytes.
    live.write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)
    upload_bytes = _build_complete_db_bytes(tmp_path)

    exits: list[int] = []

    def fake_exit(code: int) -> None:  # noqa: ARG001 - matches os._exit signature
        exits.append(code)

    monkeypatch.setattr(os, "_exit", fake_exit)

    # Run the exit-after-delay thread synchronously so the assertion below
    # sees the captured exit code without sleeping.
    def instant_start(self: threading.Thread) -> None:
        self.run()

    monkeypatch.setattr(threading.Thread, "start", instant_start)

    res = client.post(
        "/api/backup/restore",
        files={"file": ("backup.db", upload_bytes, "application/octet-stream")},
    )

    assert res.status_code == 202
    assert res.json() == {"status": "restoring"}
    assert exits == [75]
    # The swap actually happened: live now contains the uploaded payload.
    assert live.read_bytes() == upload_bytes
