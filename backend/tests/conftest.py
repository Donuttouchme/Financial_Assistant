import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
import app.models  # noqa: F401 — register models with Base.metadata


@pytest.fixture(autouse=True)
def _no_real_fx_refresh(request, monkeypatch):
    """Block all outbound frankfurter.app calls in tests.

    Patches all three entry points so tests are hermetic: lifespan refresh,
    eager-fill on transaction insert/CSV import, and manual refresh endpoint.
    Tests that exercise the real HTTP client (with their own httpx mock) opt
    out via the ``real_fx_client`` marker.
    """
    if "real_fx_client" in request.keywords:
        return

    from app.services import fx_service

    async def noop_refresh(*args, **kwargs):
        return (None, 0)

    async def noop_fetch_for_date(target):
        return {}

    async def noop_fetch_today():
        from datetime import date as _date
        return _date.today(), {}

    monkeypatch.setattr(fx_service, "refresh_today", noop_refresh)
    monkeypatch.setattr(fx_service, "fetch_rates_for_date", noop_fetch_for_date)
    monkeypatch.setattr(fx_service, "fetch_rates_for_today", noop_fetch_today)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, _):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


from fastapi.testclient import TestClient

from app.dependencies import get_current_month, get_current_user_id
from app.database import get_db
from app.main import app


@pytest.fixture
def client(db_session):
    def override_db():
        yield db_session

    def override_user():
        return 1

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user_id] = override_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def freeze_month(client):
    """Pin ``get_current_month`` to a value of the test's choosing.

    Usage:
        def test_x(client, freeze_month):
            freeze_month("2026-06")
            client.put("/api/budgets/1", json={"monthly_limit": "200"})
    """
    def _set(month: str) -> None:
        app.dependency_overrides[get_current_month] = lambda: month

    yield _set
    app.dependency_overrides.pop(get_current_month, None)
