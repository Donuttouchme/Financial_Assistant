from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


_db_url = settings.resolved_database_url()

engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False} if _db_url.startswith("sqlite") else {},
)

if _db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
