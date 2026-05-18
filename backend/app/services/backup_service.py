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

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import settings

# How many ``<live>.pre-restore-*`` snapshots to keep on disk. Older
# archives are pruned after each successful commit so a long-running install
# doesn't accumulate gigabytes of stale backups.
_PRE_RESTORE_KEEP = 5

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


# --- restore lifecycle --------------------------------------------------
#
# ``export_db`` / ``stage_restore`` / ``commit_restore`` form the three-step
# upload flow used by the backup router (Task E3). The service is strictly
# file-IO: it does NOT dispose the SQLAlchemy engine. On Windows the open
# engine holds a lock on the live DB file and ``shutil.move`` will raise a
# ``PermissionError`` — the router is responsible for calling
# ``engine.dispose()`` before invoking ``commit_restore``.


def _live_db_path() -> Path:
    """Return the on-disk live SQLite path from settings."""
    return Path(settings.resolved_db_path())


def export_db() -> bytes:
    """Return the raw bytes of the live database file.

    Reads the file directly; no SQLite handles are opened. The router can
    stream the result back to the client as a ``.db`` download.
    """
    return _live_db_path().read_bytes()


def stage_restore(uploaded: bytes) -> Path:
    """Write ``uploaded`` to ``<live>.pending`` and validate it.

    On success the pending path is returned (still on disk, untouched).
    On validation failure the pending file is removed and the underlying
    ``ValueError`` propagates so the router can return HTTP 400.
    """
    live = _live_db_path()
    pending = live.parent / f"{live.name}.pending"
    pending.write_bytes(uploaded)
    try:
        validate_uploaded_db(pending)
    except Exception:
        pending.unlink(missing_ok=True)
        raise
    return pending


def commit_restore() -> Path:
    """Atomically swap ``<live>.pending`` into the live path.

    Returns the path of the timestamped ``<live>.pre-restore-*`` archive
    that holds the previous live DB. Raises ``FileNotFoundError`` if no
    ``.pending`` is staged.

    The caller MUST have disposed the SQLAlchemy engine first — see module
    docstring.
    """
    live = _live_db_path()
    pending = live.parent / f"{live.name}.pending"
    if not pending.exists():
        raise FileNotFoundError(f"no pending restore at {pending}")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = live.parent / f"{live.name}.pre-restore-{stamp}"
    if live.exists():
        shutil.move(str(live), str(archive))
    shutil.move(str(pending), str(live))
    _prune_archives(live)
    return archive


def _prune_archives(live: Path) -> None:
    """Keep only the ``_PRE_RESTORE_KEEP`` most-recent pre-restore archives.

    Archive filenames embed a ``YYYYMMDD-HHMMSS`` timestamp, so lexicographic
    sort is equivalent to chronological order — the trailing slice is the
    newest set we want to retain.
    """
    archives = sorted(live.parent.glob(f"{live.name}.pre-restore-*"))
    for old in archives[:-_PRE_RESTORE_KEEP]:
        old.unlink()
