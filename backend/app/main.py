from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401 — register models with Base.metadata
from app.database import Base, SessionLocal, engine
from app.migrations import run_migrations
from app.routers import budgets, categories, export, health, transactions
from app.services import recurring_service


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
    yield


app = FastAPI(title="Financial Assistant API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(export.router)


# Conditional SPA mount — only in prod-local mode where the frontend has been built.
# `html=True` makes StaticFiles serve index.html for unknown paths, which is what
# the React Router expects (refresh on /transactions must not 404).
if _FRONTEND_DIST.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(_FRONTEND_DIST), html=True),
        name="frontend",
    )
