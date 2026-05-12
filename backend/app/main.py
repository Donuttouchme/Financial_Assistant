from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI

import app.models  # noqa: F401 — register models with Base.metadata
from app.database import Base, SessionLocal, engine
from app.routers import budgets, categories, export, health, transactions
from app.services import recurring_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        recurring_service.run_due_schedules(db, today=date.today())
    finally:
        db.close()
    yield


app = FastAPI(title="Financial Assistant API", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(export.router)
