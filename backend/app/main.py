import asyncio
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Scope

import app.models  # noqa: F401 — register models with Base.metadata
from app import idle
from app.database import Base, SessionLocal, engine
from app.migrations import run_migrations
from app.routers import backup, budgets, categories, csv_import, export, health, heartbeat, import_presets, recurring, transactions
from app.routers import settings as settings_router, fx as fx_router
from app.routers import forecast as forecast_router
from app.services import recurring_service, fx_service, settings_service


# Location of the built React app relative to this file:
# backend/app/main.py -> ../../frontend/dist
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    run_migrations(engine)
    db = SessionLocal()
    try:
        recurring_service.run_due_schedules(db, today=date.today())
    finally:
        db.close()

    # Seed settings row (idempotent — won't overwrite existing values)
    db = SessionLocal()
    try:
        settings_service.get_settings(db)
    finally:
        db.close()

    # Kick off FX refresh in the background (non-blocking)
    async def _refresh_fx():
        db = SessionLocal()
        try:
            await fx_service.refresh_today(db)
        finally:
            db.close()

    fx_task = asyncio.create_task(_refresh_fx())

    watchdog_task = idle.start_watchdog()
    try:
        yield
    finally:
        watchdog_task.cancel()
        try:
            await watchdog_task
        except asyncio.CancelledError:
            pass
        fx_task.cancel()
        try:
            await fx_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Financial Assistant API", version="1.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _track_activity(request, call_next):
    idle.record_activity()
    return await call_next(request)


app.include_router(health.router)
app.include_router(heartbeat.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(export.router)
app.include_router(import_presets.router)
app.include_router(csv_import.router)
app.include_router(settings_router.router)
app.include_router(fx_router.router)
app.include_router(forecast_router.router)
app.include_router(recurring.router)
app.include_router(backup.router)


# SPA fallback + cache headers.
#
# (1) StaticFiles(html=True) only serves index.html as a directory default,
#     not as a fallback for arbitrary unknown paths. A hard-refresh on
#     /dashboard would otherwise return 404. Catch 404s and serve index.html
#     so React Router can handle the route on the client.
#
# (2) The launcher rebuilds frontend/dist on every release, but the served
#     HTML always references new hashed asset filenames. If the browser
#     caches index.html, on next start it loads stale HTML pointing at the
#     previous bundle URL, and the user sees the old UI until they reload.
#     Mark index.html no-cache so the browser revalidates each load; the
#     hashed /assets/* files are content-addressed and safe to cache forever.
class _SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope):
        served_fallback = False
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as ex:
            if ex.status_code == 404 and not path.startswith("api"):
                response = await super().get_response("index.html", scope)
                served_fallback = True
            else:
                raise

        # Use content-type rather than path: path is platform-dependent
        # (Windows uses backslash) and "." for the root, which makes
        # string-prefix checks fragile.
        normalized = path.replace("\\", "/")
        is_html = response.headers.get("content-type", "").startswith("text/html")
        if served_fallback or is_html:
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        elif normalized.startswith("assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

        return response


if _FRONTEND_DIST.is_dir():
    app.mount(
        "/",
        _SPAStaticFiles(directory=str(_FRONTEND_DIST), html=True),
        name="frontend",
    )
