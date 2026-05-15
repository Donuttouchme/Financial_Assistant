import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
import app.models  # noqa: F401 — register models with Base.metadata


@pytest.fixture(autouse=True)
def _no_real_fx_refresh(monkeypatch):
    """Prevent the lifespan's FX kickoff from hitting the real network in tests."""
    from app.services import fx_service

    async def noop(*args, **kwargs):
        return (None, 0)

    monkeypatch.setattr(fx_service, "refresh_today", noop)


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

from app.dependencies import get_current_user_id
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
