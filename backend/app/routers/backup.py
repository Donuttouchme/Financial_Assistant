"""Backup download + restore endpoints.

Restore triggers ``os._exit(75)`` in a daemon thread after a short delay so
the response can flush. The launcher (``RUN.bat``) watches for exit code 75
and relaunches uvicorn — the frontend reload then picks up the swapped-in DB.

We dispose the SQLAlchemy engine BEFORE the file swap so SQLite releases the
DB file handle on Windows. If we forget, ``shutil.move`` raises PermissionError.
"""
from __future__ import annotations

import os
import threading
import time

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.database import engine
from app.services import backup_service


router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("/download")
def download_backup() -> Response:
    blob = backup_service.export_db()
    return Response(
        content=blob,
        media_type="application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="financial.db"'},
    )


def _exit_after_delay(delay_seconds: float, code: int) -> None:
    """Sleep, then hard-exit. Run in a daemon thread so the HTTP response
    flushes first."""
    time.sleep(delay_seconds)
    os._exit(code)


@router.post("/restore", status_code=202)
async def restore_backup(file: UploadFile = File(...)) -> dict[str, str]:
    data = await file.read()
    try:
        backup_service.stage_restore(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Release SQLite's file handle before the swap (Windows-critical).
    engine.dispose()
    backup_service.commit_restore()

    # Trigger uvicorn exit 75 -> RUN.bat relaunch loop. Daemon thread so the
    # response gets flushed before the process dies.
    threading.Thread(
        target=_exit_after_delay, args=(0.5, 75), daemon=True,
    ).start()
    return {"status": "restoring"}
