"""Backup / restore service.

Validates uploaded SQLite files before any restore swap. The validation set
intentionally lists EVERY user-data table the app reads at runtime — a
silently-missing table (e.g. ``fx_rates``) would let a "valid" upload pass
here, then crash the app the first time the user opens the forecast or
imports a CSV. See ``docs/superpowers/plans/2026-05-18-post-v1.2-bug-batch.md``
Task E1 for the bug report.

The list is kept in lockstep with ``backend/app/models/__init__.py`` —
adding a new model means adding its ``__tablename__`` here too.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Every user-data table the application requires at runtime. Mirrors the
# ``__tablename__`` values declared in ``app.models.*``. Keep alphabetised.
_REQUIRED_TABLES: frozenset[str] = frozenset(
    {
        "budget_limits",
        "categories",
        "fx_rates",
        "import_presets",
        "recurring_schedules",
        "settings",
        "transactions",
    }
)


def validate_uploaded_db(path: Path) -> None:
    """Validate that ``path`` points to a SQLite file with every required table.

    Raises ``ValueError`` if:
      * the file does not exist or is unreadable
      * the file is not a valid SQLite database
      * any required user-data table is missing

    The error message names the *first* missing table so the API layer can
    surface it to the user without leaking the entire schema.
    """
    p = Path(path)
    if not p.exists():
        raise ValueError(f"backup file not found: {p}")

    # SQLite files start with the literal bytes b"SQLite format 3\x00".
    try:
        with p.open("rb") as fh:
            header = fh.read(16)
    except OSError as exc:
        raise ValueError(f"unable to read backup file: {exc}") from exc
    if header != b"SQLite format 3\x00":
        raise ValueError("uploaded file is not a SQLite database")

    try:
        conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise ValueError(f"unable to open SQLite database: {exc}") from exc

    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        present = {row[0] for row in cur.fetchall()}
    except sqlite3.DatabaseError as exc:
        raise ValueError(f"corrupt SQLite database: {exc}") from exc
    finally:
        conn.close()

    missing = _REQUIRED_TABLES - present
    if missing:
        # Stable ordering so the error message is deterministic across runs.
        first = sorted(missing)[0]
        raise ValueError(
            f"backup is missing required table: {first}"
        )
