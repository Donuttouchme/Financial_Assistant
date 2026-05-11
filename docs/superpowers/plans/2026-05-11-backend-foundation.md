# Financial Assistant — Phase 1: Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully working FastAPI backend that exposes the complete REST API described in the PRD (transactions, categories, recurring schedules, budgets, CSV export, health), backed by SQLite and covered by pytest.

**Architecture:** A single FastAPI app under `/backend` with three layers: SQLAlchemy 2.0 ORM models, service modules that contain all business logic, and thin router modules that translate HTTP ↔ services. A `get_current_user_id` dependency returns a hard-coded user_id=1 today and is the single seam where authentication will plug in later. Recurring transactions are materialized on app startup via a FastAPI lifespan hook that walks the `RecurringSchedule` table.

**Tech Stack:** Python 3.10+, FastAPI 0.110+, SQLAlchemy 2.0, Pydantic v2, SQLite (via `sqlite:///./financial.db`), python-dateutil for month arithmetic, pytest + httpx TestClient for tests.

---

## Phase 1 File Structure

Created in this phase:

```
backend/
  app/
    __init__.py
    main.py                     # FastAPI app + lifespan (runs recurring sweep)
    config.py                   # Settings (DB URL, etc.)
    database.py                 # Engine, SessionLocal, Base, get_db dep
    dependencies.py             # get_current_user_id (hardcoded user_id=1)
    models/
      __init__.py               # re-exports models
      category.py
      transaction.py
      recurring_schedule.py
      budget_limit.py
    schemas/
      __init__.py
      category.py
      transaction.py
      recurring_schedule.py
      budget_limit.py
    services/
      __init__.py
      category_service.py
      transaction_service.py
      recurring_service.py
      budget_service.py
      export_service.py
    routers/
      __init__.py
      health.py
      categories.py
      transactions.py
      budgets.py
      export.py
  tests/
    __init__.py
    conftest.py                 # in-memory SQLite + TestClient fixtures
    test_category_service.py
    test_transaction_service.py
    test_recurring_service.py
    test_budget_service.py
    test_export_service.py
    test_routes/
      __init__.py
      test_health.py
      test_categories.py
      test_transactions.py
      test_budgets.py
      test_export.py
  requirements.txt
  pytest.ini
  .env.example
README.md                       # backend section only this phase
.gitignore
```

Each model file owns one entity. Services own one bounded responsibility each and stay free of HTTP concerns. Routers stay thin — they parse input, call a service, shape the response. This split keeps each file small enough to hold in working memory and isolates business logic from FastAPI plumbing so it can be unit-tested without TestClient.

---

## Task 1: Project skeleton, dependencies, tooling

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/pytest.ini`
- Create: `backend/.env.example`
- Create: `.gitignore`
- Create: `README.md`
- Create: `backend/app/__init__.py` (empty)
- Create: `backend/tests/__init__.py` (empty)

- [ ] **Step 1: Create `backend/requirements.txt`**

```text
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
pydantic==2.9.2
pydantic-settings==2.5.2
python-dateutil==2.9.0
httpx==0.27.2
pytest==8.3.3
pytest-cov==5.0.0
```

- [ ] **Step 2: Create `backend/pytest.ini`**

```ini
[pytest]
testpaths = tests
pythonpath = .
addopts = -q --strict-markers
```

`pythonpath = .` lets tests import `from app.x import y` when pytest is invoked from `/backend`.

- [ ] **Step 3: Create `backend/.env.example`**

```env
DATABASE_URL=sqlite:///./financial.db
```

- [ ] **Step 4: Create root `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/
.env

# SQLite
*.db
*.db-journal

# Node (Phase 2)
node_modules/
frontend/dist/

# Editors
.vscode/
.idea/

# Coverage
.coverage
htmlcov/
.pytest_cache/
```

- [ ] **Step 5: Create root `README.md` skeleton**

```markdown
# Financial Assistant

Personal finance tracker. Single user, local-first.

## Phase 1: Backend (this milestone)

### Setup

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate   # PowerShell on Windows
pip install -r requirements.txt
copy .env.example .env
```

### Run

```bash
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Tests

```bash
pytest
```
```

- [ ] **Step 6: Create empty package init files**

Create `backend/app/__init__.py` and `backend/tests/__init__.py` as empty files.

- [ ] **Step 7: Verify install**

Run (from `backend/`):
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pytest
```
Expected: `pytest` reports `no tests ran` (exit 5) — no failures.

- [ ] **Step 8: Commit**

```bash
git init
git add .
git commit -m "chore: bootstrap backend project skeleton"
```

---

## Task 2: Config, database engine, base model, dev seed user

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/dependencies.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Write the failing conftest sanity test**

Create `backend/tests/test_conftest_smoke.py`:

```python
from sqlalchemy import text


def test_db_session_fixture_provides_working_connection(db_session):
    result = db_session.execute(text("SELECT 1")).scalar()
    assert result == 1
```

- [ ] **Step 2: Run it to verify failure**

Run: `pytest tests/test_conftest_smoke.py -v`
Expected: FAIL — fixture `db_session` not found.

- [ ] **Step 3: Implement `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./financial.db"


settings = Settings()
```

- [ ] **Step 4: Implement `backend/app/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Implement `backend/app/dependencies.py`**

```python
DEFAULT_USER_ID = 1


def get_current_user_id() -> int:
    """Single-user mode: always returns 1. Replace with auth integration later."""
    return DEFAULT_USER_ID
```

- [ ] **Step 6: Implement `backend/app/models/__init__.py`**

```python
# Re-exported as models land in later tasks.
```

- [ ] **Step 7: Implement `backend/tests/conftest.py`**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
import app.models  # noqa: F401 — register models with Base.metadata


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
```

`StaticPool` keeps the in-memory DB alive across `session.execute` calls. `import app.models` ensures every model file registers its table on `Base.metadata` before `create_all` runs — once models exist in later tasks they need to be re-exported from `app/models/__init__.py`.

- [ ] **Step 8: Run conftest smoke test**

Run: `pytest tests/test_conftest_smoke.py -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/app/config.py backend/app/database.py backend/app/dependencies.py backend/app/models/__init__.py backend/tests/conftest.py backend/tests/test_conftest_smoke.py
git commit -m "feat(backend): add config, database, base model and test fixtures"
```

---

## Task 3: Category model, schema, service (TDD)

**Files:**
- Create: `backend/app/models/category.py`
- Create: `backend/app/schemas/category.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/category_service.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_category_service.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_category_service.py`:

```python
import pytest

from app.services import category_service


def test_create_category_persists_with_user_id(db_session):
    cat = category_service.create_category(db_session, user_id=1, name="Groceries")
    assert cat.id is not None
    assert cat.name == "Groceries"
    assert cat.user_id == 1


def test_list_categories_returns_only_users_own(db_session):
    category_service.create_category(db_session, user_id=1, name="Groceries")
    category_service.create_category(db_session, user_id=1, name="Rent")
    category_service.create_category(db_session, user_id=2, name="Other user's cat")

    names = [c.name for c in category_service.list_categories(db_session, user_id=1)]
    assert sorted(names) == ["Groceries", "Rent"]


def test_create_category_rejects_duplicate_name_for_same_user(db_session):
    category_service.create_category(db_session, user_id=1, name="Groceries")
    with pytest.raises(ValueError, match="already exists"):
        category_service.create_category(db_session, user_id=1, name="Groceries")


def test_delete_category_removes_it(db_session):
    cat = category_service.create_category(db_session, user_id=1, name="Misc")
    category_service.delete_category(db_session, user_id=1, category_id=cat.id)
    assert category_service.list_categories(db_session, user_id=1) == []


def test_delete_unknown_category_raises_lookup_error(db_session):
    with pytest.raises(LookupError):
        category_service.delete_category(db_session, user_id=1, category_id=999)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_category_service.py -v`
Expected: FAIL — `app.services` import errors.

- [ ] **Step 3: Implement `backend/app/models/category.py`**

```python
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_category_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 4: Update `backend/app/models/__init__.py`**

```python
from app.models.category import Category

__all__ = ["Category"]
```

- [ ] **Step 5: Implement `backend/app/schemas/__init__.py`** (empty file)

- [ ] **Step 6: Implement `backend/app/schemas/category.py`**

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
```

- [ ] **Step 7: Implement `backend/app/services/__init__.py`** (empty file)

- [ ] **Step 8: Implement `backend/app/services/category_service.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category


def create_category(db: Session, *, user_id: int, name: str) -> Category:
    existing = db.execute(
        select(Category).where(Category.user_id == user_id, Category.name == name)
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError(f"Category '{name}' already exists for user {user_id}")

    cat = Category(user_id=user_id, name=name)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def list_categories(db: Session, *, user_id: int) -> list[Category]:
    rows = db.execute(
        select(Category).where(Category.user_id == user_id).order_by(Category.name)
    ).scalars().all()
    return list(rows)


def get_category(db: Session, *, user_id: int, category_id: int) -> Category | None:
    return db.execute(
        select(Category).where(Category.user_id == user_id, Category.id == category_id)
    ).scalar_one_or_none()


def delete_category(db: Session, *, user_id: int, category_id: int) -> None:
    cat = get_category(db, user_id=user_id, category_id=category_id)
    if cat is None:
        raise LookupError(f"Category {category_id} not found for user {user_id}")
    db.delete(cat)
    db.commit()
```

- [ ] **Step 9: Run tests to verify pass**

Run: `pytest tests/test_category_service.py -v`
Expected: 5 passed.

- [ ] **Step 10: Commit**

```bash
git add backend/app/models/category.py backend/app/models/__init__.py backend/app/schemas backend/app/services backend/tests/test_category_service.py
git commit -m "feat(backend): add Category model, schema and service"
```

---

## Task 4: Transaction model, schema, service (TDD)

**Files:**
- Create: `backend/app/models/transaction.py`
- Create: `backend/app/schemas/transaction.py`
- Create: `backend/app/services/transaction_service.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_transaction_service.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_transaction_service.py`:

```python
from datetime import date
from decimal import Decimal

import pytest

from app.services import category_service, transaction_service


@pytest.fixture
def groceries(db_session):
    return category_service.create_category(db_session, user_id=1, name="Groceries")


def test_create_transaction_persists_fields(db_session, groceries):
    tx = transaction_service.create_transaction(
        db_session,
        user_id=1,
        amount=Decimal("12.34"),
        tx_date=date(2026, 5, 10),
        category_id=groceries.id,
        description="Milk",
        is_recurring=False,
    )
    assert tx.id is not None
    assert tx.amount == Decimal("12.34")
    assert tx.date == date(2026, 5, 10)
    assert tx.category_id == groceries.id
    assert tx.description == "Milk"
    assert tx.user_id == 1


def test_create_transaction_rejects_non_positive_amount(db_session, groceries):
    with pytest.raises(ValueError, match="amount"):
        transaction_service.create_transaction(
            db_session,
            user_id=1,
            amount=Decimal("0"),
            tx_date=date(2026, 5, 10),
            category_id=groceries.id,
            description="",
        )


def test_create_transaction_rejects_unknown_category(db_session):
    with pytest.raises(LookupError):
        transaction_service.create_transaction(
            db_session,
            user_id=1,
            amount=Decimal("10"),
            tx_date=date(2026, 5, 10),
            category_id=999,
            description="x",
        )


def test_list_transactions_filters_by_month(db_session, groceries):
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("5"), tx_date=date(2026, 5, 1),
        category_id=groceries.id, description="May 1",
    )
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("5"), tx_date=date(2026, 5, 31),
        category_id=groceries.id, description="May 31",
    )
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("5"), tx_date=date(2026, 6, 1),
        category_id=groceries.id, description="June",
    )

    may = transaction_service.list_transactions(db_session, user_id=1, month="2026-05")
    assert [tx.description for tx in may] == ["May 31", "May 1"]


def test_list_transactions_filters_by_category(db_session, groceries):
    rent = category_service.create_category(db_session, user_id=1, name="Rent")
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("5"), tx_date=date(2026, 5, 1),
        category_id=groceries.id, description="Food",
    )
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500"), tx_date=date(2026, 5, 1),
        category_id=rent.id, description="May rent",
    )

    only_rent = transaction_service.list_transactions(db_session, user_id=1, category_id=rent.id)
    assert [tx.description for tx in only_rent] == ["May rent"]


def test_update_transaction_changes_fields(db_session, groceries):
    tx = transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("5"), tx_date=date(2026, 5, 1),
        category_id=groceries.id, description="Old",
    )

    updated = transaction_service.update_transaction(
        db_session, user_id=1, transaction_id=tx.id,
        amount=Decimal("9.99"), description="New",
    )
    assert updated.amount == Decimal("9.99")
    assert updated.description == "New"
    assert updated.date == date(2026, 5, 1)  # unchanged


def test_delete_transaction_removes_it(db_session, groceries):
    tx = transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("5"), tx_date=date(2026, 5, 1),
        category_id=groceries.id, description="X",
    )
    transaction_service.delete_transaction(db_session, user_id=1, transaction_id=tx.id)
    assert transaction_service.list_transactions(db_session, user_id=1) == []
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_transaction_service.py -v`
Expected: FAIL — `transaction_service` not found.

- [ ] **Step 3: Implement `backend/app/models/transaction.py`**

```python
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    category = relationship("Category")
```

- [ ] **Step 4: Update `backend/app/models/__init__.py`**

```python
from app.models.category import Category
from app.models.transaction import Transaction

__all__ = ["Category", "Transaction"]
```

- [ ] **Step 5: Implement `backend/app/schemas/transaction.py`**

```python
from datetime import date as date_type, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    amount: Decimal = Field(gt=Decimal("0"))
    date: date_type
    category_id: int
    description: str = Field(default="", max_length=255)
    is_recurring: bool = False


class TransactionUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=Decimal("0"))
    date: date_type | None = None
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=255)


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    date: date_type
    category_id: int
    description: str
    is_recurring: bool
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 6: Implement `backend/app/services/transaction_service.py`**

```python
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction


def _month_bounds(month: str) -> tuple[date, date]:
    """'YYYY-MM' -> (first_day, first_day_of_next_month)."""
    year, mo = map(int, month.split("-"))
    start = date(year, mo, 1)
    end = date(year + (mo // 12), (mo % 12) + 1, 1)
    return start, end


def _ensure_category(db: Session, *, user_id: int, category_id: int) -> Category:
    cat = db.execute(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    ).scalar_one_or_none()
    if cat is None:
        raise LookupError(f"Category {category_id} not found for user {user_id}")
    return cat


_TWO_PLACES = Decimal("0.01")


def _quantize_money(amount: Decimal) -> Decimal:
    return amount.quantize(_TWO_PLACES)


def create_transaction(
    db: Session,
    *,
    user_id: int,
    amount: Decimal,
    tx_date: date,
    category_id: int,
    description: str,
    is_recurring: bool = False,
) -> Transaction:
    if amount <= Decimal("0"):
        raise ValueError("amount must be > 0")
    _ensure_category(db, user_id=user_id, category_id=category_id)

    tx = Transaction(
        user_id=user_id,
        amount=_quantize_money(amount),
        date=tx_date,
        category_id=category_id,
        description=description,
        is_recurring=is_recurring,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def list_transactions(
    db: Session,
    *,
    user_id: int,
    month: str | None = None,
    category_id: int | None = None,
) -> list[Transaction]:
    stmt = select(Transaction).where(Transaction.user_id == user_id)
    if month:
        start, end = _month_bounds(month)
        stmt = stmt.where(Transaction.date >= start, Transaction.date < end)
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    stmt = stmt.order_by(Transaction.date.desc(), Transaction.id.desc())
    return list(db.execute(stmt).scalars().all())


def get_transaction(db: Session, *, user_id: int, transaction_id: int) -> Transaction | None:
    return db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id, Transaction.user_id == user_id
        )
    ).scalar_one_or_none()


def update_transaction(
    db: Session,
    *,
    user_id: int,
    transaction_id: int,
    amount: Decimal | None = None,
    tx_date: date | None = None,
    category_id: int | None = None,
    description: str | None = None,
) -> Transaction:
    tx = get_transaction(db, user_id=user_id, transaction_id=transaction_id)
    if tx is None:
        raise LookupError(f"Transaction {transaction_id} not found for user {user_id}")

    if amount is not None:
        if amount <= Decimal("0"):
            raise ValueError("amount must be > 0")
        tx.amount = _quantize_money(amount)
    if tx_date is not None:
        tx.date = tx_date
    if category_id is not None:
        _ensure_category(db, user_id=user_id, category_id=category_id)
        tx.category_id = category_id
    if description is not None:
        tx.description = description

    db.commit()
    db.refresh(tx)
    return tx


def delete_transaction(db: Session, *, user_id: int, transaction_id: int) -> None:
    tx = get_transaction(db, user_id=user_id, transaction_id=transaction_id)
    if tx is None:
        raise LookupError(f"Transaction {transaction_id} not found for user {user_id}")
    db.delete(tx)
    db.commit()
```

- [ ] **Step 7: Run tests to verify pass**

Run: `pytest tests/test_transaction_service.py -v`
Expected: 7 passed.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/transaction.py backend/app/models/__init__.py backend/app/schemas/transaction.py backend/app/services/transaction_service.py backend/tests/test_transaction_service.py
git commit -m "feat(backend): add Transaction model, schema and service"
```

---

## Task 5: RecurringSchedule model, schema, service (TDD)

When `transaction_service.create_transaction(..., is_recurring=True)` runs we want a `RecurringSchedule` row created automatically. The schedule remembers the template (amount, category, description) and the next date a new transaction should be materialized. A standalone `run_due_schedules()` function — called on app startup — fires all overdue schedules and bumps each one's `next_occurrence_date` until it sits in the future.

**Files:**
- Create: `backend/app/models/recurring_schedule.py`
- Create: `backend/app/schemas/recurring_schedule.py`
- Create: `backend/app/services/recurring_service.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/services/transaction_service.py`
- Create: `backend/tests/test_recurring_service.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_recurring_service.py`:

```python
from datetime import date
from decimal import Decimal

import pytest
from dateutil.relativedelta import relativedelta

from app.services import category_service, recurring_service, transaction_service


@pytest.fixture
def rent_category(db_session):
    return category_service.create_category(db_session, user_id=1, name="Rent")


def test_create_recurring_transaction_creates_schedule(db_session, rent_category):
    tx = transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500"), tx_date=date(2026, 5, 1),
        category_id=rent_category.id, description="Rent", is_recurring=True,
    )
    schedules = recurring_service.list_schedules(db_session, user_id=1)
    assert len(schedules) == 1
    sched = schedules[0]
    assert sched.transaction_id == tx.id
    assert sched.next_occurrence_date == date(2026, 6, 1)
    assert sched.amount == Decimal("500")
    assert sched.category_id == rent_category.id


def test_non_recurring_transaction_creates_no_schedule(db_session, rent_category):
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("5"), tx_date=date(2026, 5, 1),
        category_id=rent_category.id, description="One-off", is_recurring=False,
    )
    assert recurring_service.list_schedules(db_session, user_id=1) == []


def test_run_due_schedules_creates_transactions_until_future(db_session, rent_category):
    # Seed: schedule with next_occurrence_date in the past (March), today = May 15
    tx = transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500"), tx_date=date(2026, 2, 1),
        category_id=rent_category.id, description="Rent", is_recurring=True,
    )
    sched = recurring_service.list_schedules(db_session, user_id=1)[0]
    assert sched.next_occurrence_date == date(2026, 3, 1)

    created = recurring_service.run_due_schedules(db_session, today=date(2026, 5, 15))

    # March, April, May should have been materialized.
    assert len(created) == 3
    assert [t.date for t in created] == [date(2026, 3, 1), date(2026, 4, 1), date(2026, 5, 1)]
    for new_tx in created:
        assert new_tx.amount == Decimal("500")
        assert new_tx.category_id == rent_category.id
        assert new_tx.is_recurring is False  # generated children are not themselves recurring

    db_session.refresh(sched)
    assert sched.next_occurrence_date == date(2026, 6, 1)

    # Idempotency: rerun on same day generates nothing more.
    again = recurring_service.run_due_schedules(db_session, today=date(2026, 5, 15))
    assert again == []


def test_run_due_schedules_skips_future_only_schedules(db_session, rent_category):
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500"), tx_date=date(2026, 12, 1),
        category_id=rent_category.id, description="Future rent", is_recurring=True,
    )
    created = recurring_service.run_due_schedules(db_session, today=date(2026, 5, 15))
    assert created == []


def test_delete_recurring_transaction_removes_its_schedule(db_session, rent_category):
    tx = transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500"), tx_date=date(2026, 5, 1),
        category_id=rent_category.id, description="Rent", is_recurring=True,
    )
    transaction_service.delete_transaction(db_session, user_id=1, transaction_id=tx.id)
    assert recurring_service.list_schedules(db_session, user_id=1) == []
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_recurring_service.py -v`
Expected: FAIL — `recurring_service` import error.

- [ ] **Step 3: Implement `backend/app/models/recurring_schedule.py`**

```python
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecurringSchedule(Base):
    __tablename__ = "recurring_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_occurrence_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    frequency: Mapped[str] = mapped_column(String(16), nullable=False, default="monthly")
```

- [ ] **Step 4: Update `backend/app/models/__init__.py`**

```python
from app.models.category import Category
from app.models.recurring_schedule import RecurringSchedule
from app.models.transaction import Transaction

__all__ = ["Category", "RecurringSchedule", "Transaction"]
```

- [ ] **Step 5: Implement `backend/app/schemas/recurring_schedule.py`**

```python
from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RecurringScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: int
    amount: Decimal
    category_id: int
    description: str
    start_date: date_type
    next_occurrence_date: date_type
    frequency: str
```

- [ ] **Step 6: Implement `backend/app/services/recurring_service.py`**

```python
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recurring_schedule import RecurringSchedule
from app.models.transaction import Transaction


def create_schedule_for_transaction(db: Session, *, transaction: Transaction) -> RecurringSchedule:
    sched = RecurringSchedule(
        user_id=transaction.user_id,
        transaction_id=transaction.id,
        amount=transaction.amount,
        category_id=transaction.category_id,
        description=transaction.description,
        start_date=transaction.date,
        next_occurrence_date=transaction.date + relativedelta(months=1),
        frequency="monthly",
    )
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return sched


def list_schedules(db: Session, *, user_id: int) -> list[RecurringSchedule]:
    return list(
        db.execute(
            select(RecurringSchedule).where(RecurringSchedule.user_id == user_id)
        ).scalars().all()
    )


def run_due_schedules(db: Session, *, today: date) -> list[Transaction]:
    """For every schedule with next_occurrence_date <= today, materialize a transaction
    and advance next_occurrence_date by one month, repeating until it sits in the future.
    Returns the list of newly created transactions in chronological order."""
    due_schedules = db.execute(
        select(RecurringSchedule).where(RecurringSchedule.next_occurrence_date <= today)
    ).scalars().all()

    created: list[Transaction] = []
    for sched in due_schedules:
        while sched.next_occurrence_date <= today:
            new_tx = Transaction(
                user_id=sched.user_id,
                amount=sched.amount,
                date=sched.next_occurrence_date,
                category_id=sched.category_id,
                description=sched.description,
                is_recurring=False,
            )
            db.add(new_tx)
            created.append(new_tx)
            sched.next_occurrence_date = sched.next_occurrence_date + relativedelta(months=1)
    db.commit()
    for tx in created:
        db.refresh(tx)
    created.sort(key=lambda t: t.date)
    return created
```

- [ ] **Step 7: Wire schedule creation into `transaction_service.create_transaction`**

Modify `backend/app/services/transaction_service.py`. Replace the body of `create_transaction` so that after the transaction is committed, a schedule is created when `is_recurring=True`. Also update `delete_transaction` so the cascade on `recurring_schedules.transaction_id` cleans up the schedule (no extra code needed thanks to `ondelete="CASCADE"`).

Replace the existing `create_transaction` with:

```python
def create_transaction(
    db: Session,
    *,
    user_id: int,
    amount: Decimal,
    tx_date: date,
    category_id: int,
    description: str,
    is_recurring: bool = False,
) -> Transaction:
    if amount <= Decimal("0"):
        raise ValueError("amount must be > 0")
    _ensure_category(db, user_id=user_id, category_id=category_id)

    tx = Transaction(
        user_id=user_id,
        amount=amount,
        date=tx_date,
        category_id=category_id,
        description=description,
        is_recurring=is_recurring,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    if is_recurring:
        # Imported lazily to avoid a circular import.
        from app.services import recurring_service
        recurring_service.create_schedule_for_transaction(db, transaction=tx)

    return tx
```

SQLite enforces `ON DELETE CASCADE` only when `PRAGMA foreign_keys=ON`. Add this to `backend/app/database.py` right after the `engine = create_engine(...)` block:

```python
from sqlalchemy import event


@event.listens_for(engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

Wrap that listener in `if settings.database_url.startswith("sqlite"):` so PostgreSQL deployments don't trip on it. Repeat the listener registration on the test in-memory engine inside `conftest.py` — add immediately after `engine = create_engine(...)`:

```python
from sqlalchemy import event

@event.listens_for(engine, "connect")
def _fk_on(dbapi_connection, _):
    cur = dbapi_connection.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()
```

- [ ] **Step 8: Run all tests**

Run: `pytest -v`
Expected: every test passes (category, transaction, recurring, smoke).

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/recurring_schedule.py backend/app/models/__init__.py backend/app/schemas/recurring_schedule.py backend/app/services/recurring_service.py backend/app/services/transaction_service.py backend/app/database.py backend/tests/conftest.py backend/tests/test_recurring_service.py
git commit -m "feat(backend): add RecurringSchedule with auto-materialization on startup"
```

---

## Task 6: BudgetLimit model, schema, service (TDD)

PRD: `PUT /api/budgets/{category_id}` upserts a monthly limit and `GET /api/budgets?month=YYYY-MM` returns all budgets for that month *with* current spending and overage. Service layer must expose those two operations plus the overage calculation that the dashboard alert will consume.

**Files:**
- Create: `backend/app/models/budget_limit.py`
- Create: `backend/app/schemas/budget_limit.py`
- Create: `backend/app/services/budget_service.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_budget_service.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_budget_service.py`:

```python
from datetime import date
from decimal import Decimal

import pytest

from app.services import budget_service, category_service, transaction_service


@pytest.fixture
def groceries(db_session):
    return category_service.create_category(db_session, user_id=1, name="Groceries")


def test_set_budget_creates_record(db_session, groceries):
    b = budget_service.set_budget(
        db_session, user_id=1, category_id=groceries.id,
        month="2026-05", monthly_limit=Decimal("200"),
    )
    assert b.id is not None
    assert b.monthly_limit == Decimal("200")
    assert b.month == "2026-05"


def test_set_budget_updates_existing(db_session, groceries):
    budget_service.set_budget(
        db_session, user_id=1, category_id=groceries.id,
        month="2026-05", monthly_limit=Decimal("200"),
    )
    updated = budget_service.set_budget(
        db_session, user_id=1, category_id=groceries.id,
        month="2026-05", monthly_limit=Decimal("250"),
    )
    assert updated.monthly_limit == Decimal("250")

    all_budgets = budget_service.list_budgets_with_spending(
        db_session, user_id=1, month="2026-05"
    )
    assert len(all_budgets) == 1


def test_set_budget_rejects_unknown_category(db_session):
    with pytest.raises(LookupError):
        budget_service.set_budget(
            db_session, user_id=1, category_id=999,
            month="2026-05", monthly_limit=Decimal("10"),
        )


def test_set_budget_rejects_bad_month_format(db_session, groceries):
    with pytest.raises(ValueError, match="month"):
        budget_service.set_budget(
            db_session, user_id=1, category_id=groceries.id,
            month="2026/05", monthly_limit=Decimal("10"),
        )


def test_list_budgets_includes_spent_and_overage(db_session, groceries):
    budget_service.set_budget(
        db_session, user_id=1, category_id=groceries.id,
        month="2026-05", monthly_limit=Decimal("100"),
    )
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("60"), tx_date=date(2026, 5, 3),
        category_id=groceries.id, description="Food",
    )
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("70"), tx_date=date(2026, 5, 10),
        category_id=groceries.id, description="More food",
    )

    rows = budget_service.list_budgets_with_spending(db_session, user_id=1, month="2026-05")
    assert len(rows) == 1
    assert rows[0].category_id == groceries.id
    assert rows[0].monthly_limit == Decimal("100")
    assert rows[0].spent == Decimal("130")
    assert rows[0].over_budget is True
    assert rows[0].overage == Decimal("30")


def test_list_budgets_excludes_transactions_outside_month(db_session, groceries):
    budget_service.set_budget(
        db_session, user_id=1, category_id=groceries.id,
        month="2026-05", monthly_limit=Decimal("100"),
    )
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("999"), tx_date=date(2026, 4, 30),
        category_id=groceries.id, description="April",
    )
    rows = budget_service.list_budgets_with_spending(db_session, user_id=1, month="2026-05")
    assert rows[0].spent == Decimal("0")
    assert rows[0].over_budget is False
    assert rows[0].overage == Decimal("0")
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_budget_service.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `backend/app/models/budget_limit.py`**

```python
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BudgetLimit(Base):
    __tablename__ = "budget_limits"
    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "month", name="uq_budget_user_cat_month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM
    monthly_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
```

- [ ] **Step 4: Update `backend/app/models/__init__.py`**

```python
from app.models.budget_limit import BudgetLimit
from app.models.category import Category
from app.models.recurring_schedule import RecurringSchedule
from app.models.transaction import Transaction

__all__ = ["BudgetLimit", "Category", "RecurringSchedule", "Transaction"]
```

- [ ] **Step 5: Implement `backend/app/schemas/budget_limit.py`**

```python
from dataclasses import dataclass
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BudgetSet(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    monthly_limit: Decimal = Field(ge=Decimal("0"))


class BudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    month: str
    monthly_limit: Decimal


class BudgetWithSpending(BaseModel):
    category_id: int
    category_name: str
    month: str
    monthly_limit: Decimal
    spent: Decimal
    over_budget: bool
    overage: Decimal


@dataclass
class BudgetWithSpendingRow:
    """Service-layer representation (services don't import schemas)."""
    category_id: int
    category_name: str
    month: str
    monthly_limit: Decimal
    spent: Decimal
    over_budget: bool
    overage: Decimal
```

- [ ] **Step 6: Implement `backend/app/services/budget_service.py`**

```python
import re
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.budget_limit import BudgetLimit
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.budget_limit import BudgetWithSpendingRow

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _validate_month(month: str) -> None:
    if not _MONTH_RE.match(month):
        raise ValueError(f"month must be YYYY-MM, got {month!r}")


def _ensure_category(db: Session, *, user_id: int, category_id: int) -> Category:
    cat = db.execute(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    ).scalar_one_or_none()
    if cat is None:
        raise LookupError(f"Category {category_id} not found for user {user_id}")
    return cat


def set_budget(
    db: Session,
    *,
    user_id: int,
    category_id: int,
    month: str,
    monthly_limit: Decimal,
) -> BudgetLimit:
    _validate_month(month)
    _ensure_category(db, user_id=user_id, category_id=category_id)
    monthly_limit = monthly_limit.quantize(Decimal("0.01"))

    existing = db.execute(
        select(BudgetLimit).where(
            BudgetLimit.user_id == user_id,
            BudgetLimit.category_id == category_id,
            BudgetLimit.month == month,
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.monthly_limit = monthly_limit
        db.commit()
        db.refresh(existing)
        return existing

    budget = BudgetLimit(
        user_id=user_id, category_id=category_id, month=month, monthly_limit=monthly_limit
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def _month_bounds(month: str):
    from datetime import date
    year, mo = map(int, month.split("-"))
    start = date(year, mo, 1)
    end = date(year + (mo // 12), (mo % 12) + 1, 1)
    return start, end


def list_budgets_with_spending(
    db: Session, *, user_id: int, month: str
) -> list[BudgetWithSpendingRow]:
    _validate_month(month)
    start, end = _month_bounds(month)

    spent_subq = (
        select(
            Transaction.category_id.label("category_id"),
            func.coalesce(func.sum(Transaction.amount), 0).label("spent"),
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.date >= start,
            Transaction.date < end,
        )
        .group_by(Transaction.category_id)
        .subquery()
    )

    rows = db.execute(
        select(BudgetLimit, Category.name, spent_subq.c.spent)
        .join(Category, Category.id == BudgetLimit.category_id)
        .outerjoin(spent_subq, spent_subq.c.category_id == BudgetLimit.category_id)
        .where(BudgetLimit.user_id == user_id, BudgetLimit.month == month)
    ).all()

    two = Decimal("0.01")
    result: list[BudgetWithSpendingRow] = []
    for budget, cat_name, spent in rows:
        spent_dec = (Decimal(spent) if spent is not None else Decimal("0")).quantize(two)
        limit = budget.monthly_limit.quantize(two)
        overage = (spent_dec - limit).quantize(two) if spent_dec > limit else Decimal("0.00")
        result.append(
            BudgetWithSpendingRow(
                category_id=budget.category_id,
                category_name=cat_name,
                month=budget.month,
                monthly_limit=limit,
                spent=spent_dec,
                over_budget=spent_dec > limit,
                overage=overage,
            )
        )
    return result
```

- [ ] **Step 7: Run tests to verify pass**

Run: `pytest tests/test_budget_service.py -v`
Expected: 6 passed.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/budget_limit.py backend/app/models/__init__.py backend/app/schemas/budget_limit.py backend/app/services/budget_service.py backend/tests/test_budget_service.py
git commit -m "feat(backend): add BudgetLimit with monthly spending/overage calculation"
```

---

## Task 7: CSV export service (TDD)

**Files:**
- Create: `backend/app/services/export_service.py`
- Create: `backend/tests/test_export_service.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_export_service.py`:

```python
import csv
import io
from datetime import date
from decimal import Decimal

from app.services import category_service, export_service, transaction_service


def test_export_csv_writes_expected_header_and_rows(db_session):
    groceries = category_service.create_category(db_session, user_id=1, name="Groceries")
    rent = category_service.create_category(db_session, user_id=1, name="Rent")
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("12.34"), tx_date=date(2026, 5, 3),
        category_id=groceries.id, description="Milk",
    )
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500.00"), tx_date=date(2026, 5, 1),
        category_id=rent.id, description="May rent",
    )

    csv_text = export_service.export_transactions_csv(db_session, user_id=1, month="2026-05")

    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert rows[0] == ["date", "category", "description", "amount"]
    assert rows[1] == ["2026-05-03", "Groceries", "Milk", "12.34"]
    assert rows[2] == ["2026-05-01", "Rent", "May rent", "500.00"]


def test_export_csv_returns_header_only_when_no_transactions(db_session):
    csv_text = export_service.export_transactions_csv(db_session, user_id=1, month="2026-05")
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert rows == [["date", "category", "description", "amount"]]
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_export_service.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `backend/app/services/export_service.py`**

```python
import csv
import io

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction
from app.services.transaction_service import _month_bounds


def export_transactions_csv(db: Session, *, user_id: int, month: str | None = None) -> str:
    stmt = (
        select(Transaction, Category.name)
        .join(Category, Category.id == Transaction.category_id)
        .where(Transaction.user_id == user_id)
    )
    if month:
        start, end = _month_bounds(month)
        stmt = stmt.where(Transaction.date >= start, Transaction.date < end)
    stmt = stmt.order_by(Transaction.date.desc(), Transaction.id.desc())

    rows = db.execute(stmt).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "category", "description", "amount"])
    for tx, cat_name in rows:
        writer.writerow([
            tx.date.isoformat(),
            cat_name,
            tx.description,
            f"{tx.amount:.2f}",
        ])
    return buf.getvalue()
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_export_service.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/export_service.py backend/tests/test_export_service.py
git commit -m "feat(backend): add CSV export service"
```

---

## Task 8: FastAPI app skeleton + Health router (TDD)

This task wires `app.main:app`, mounts a `/api` prefix, adds the `get_current_user_id` and `get_db` dependencies for routers to consume, and adds a TestClient fixture to conftest. We start with the trivial `/api/health` endpoint so routing infrastructure is proven before adding real endpoints.

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/health.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/tests/test_routes/__init__.py`
- Create: `backend/tests/test_routes/test_health.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_routes/test_health.py`:

```python
def test_health_returns_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

Also create `backend/tests/test_routes/__init__.py` (empty).

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_routes/test_health.py -v`
Expected: FAIL — `client` fixture missing.

- [ ] **Step 3: Implement `backend/app/routers/__init__.py`** (empty file)

- [ ] **Step 4: Implement `backend/app/routers/health.py`**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 5: Implement `backend/app/main.py`**

```python
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI

from app.database import Base, SessionLocal, engine
from app.routers import health
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
```

- [ ] **Step 6: Update `backend/tests/conftest.py` to add a TestClient fixture**

Append (at the bottom of the existing file):

```python
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
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

Using `with TestClient(app) as c:` triggers the lifespan against the in-memory DB, exercising the recurring sweep too.

- [ ] **Step 7: Run health test**

Run: `pytest tests/test_routes/test_health.py -v`
Expected: PASS.

- [ ] **Step 8: Run the whole suite**

Run: `pytest -v`
Expected: every test still passes.

- [ ] **Step 9: Commit**

```bash
git add backend/app/main.py backend/app/routers backend/tests/conftest.py backend/tests/test_routes
git commit -m "feat(backend): scaffold FastAPI app with lifespan, dependencies and health endpoint"
```

---

## Task 9: Categories router (TDD)

Endpoints from PRD: `GET /api/categories`, `POST /api/categories`, `DELETE /api/categories/{id}`. PRD also notes that delete must fail if the category is referenced by any transaction.

**Files:**
- Create: `backend/app/routers/categories.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/category_service.py`
- Create: `backend/tests/test_routes/test_categories.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_routes/test_categories.py`:

```python
from datetime import date
from decimal import Decimal

from app.services import transaction_service


def test_create_category_returns_201_with_payload(client):
    response = client.post("/api/categories", json={"name": "Groceries"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Groceries"
    assert "id" in body


def test_list_categories_returns_all_users_categories(client):
    client.post("/api/categories", json={"name": "Groceries"})
    client.post("/api/categories", json={"name": "Rent"})

    response = client.get("/api/categories")
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert sorted(names) == ["Groceries", "Rent"]


def test_create_duplicate_category_returns_400(client):
    client.post("/api/categories", json={"name": "Groceries"})
    response = client.post("/api/categories", json={"name": "Groceries"})
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_category_rejects_empty_name(client):
    response = client.post("/api/categories", json={"name": ""})
    assert response.status_code == 422


def test_delete_category_returns_204(client):
    cat_id = client.post("/api/categories", json={"name": "Misc"}).json()["id"]
    response = client.delete(f"/api/categories/{cat_id}")
    assert response.status_code == 204

    listed = client.get("/api/categories").json()
    assert listed == []


def test_delete_unknown_category_returns_404(client):
    response = client.delete("/api/categories/9999")
    assert response.status_code == 404


def test_delete_category_referenced_by_transaction_returns_409(client, db_session):
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("5"), tx_date=date(2026, 5, 1),
        category_id=cat_id, description="x",
    )
    response = client.delete(f"/api/categories/{cat_id}")
    assert response.status_code == 409
    assert "in use" in response.json()["detail"].lower()
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_routes/test_categories.py -v`
Expected: 404s on all routes — router not mounted.

- [ ] **Step 3: Extend `category_service.delete_category` to detect references**

Modify `backend/app/services/category_service.py`. Replace the existing `delete_category` with:

```python
def delete_category(db: Session, *, user_id: int, category_id: int) -> None:
    cat = get_category(db, user_id=user_id, category_id=category_id)
    if cat is None:
        raise LookupError(f"Category {category_id} not found for user {user_id}")

    from app.models.transaction import Transaction
    in_use = db.execute(
        select(Transaction.id).where(
            Transaction.user_id == user_id, Transaction.category_id == category_id
        ).limit(1)
    ).scalar_one_or_none()
    if in_use is not None:
        raise PermissionError(f"Category {category_id} is in use by transactions")

    db.delete(cat)
    db.commit()
```

Re-run `pytest tests/test_category_service.py -v` to confirm prior tests still pass.

- [ ] **Step 4: Implement `backend/app/routers/categories.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.category import CategoryCreate, CategoryRead
from app.services import category_service

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return category_service.list_categories(db, user_id=user_id)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return category_service.create_category(db, user_id=user_id, name=payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        category_service.delete_category(db, user_id=user_id, category_id=category_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
```

- [ ] **Step 5: Mount router in `backend/app/main.py`**

Replace the `app.include_router(...)` line with:

```python
from app.routers import categories, health

app.include_router(health.router)
app.include_router(categories.router)
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_routes/test_categories.py -v`
Expected: 7 passed.

- [ ] **Step 7: Full suite**

Run: `pytest -v`
Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/categories.py backend/app/main.py backend/app/services/category_service.py backend/tests/test_routes/test_categories.py
git commit -m "feat(backend): add categories REST endpoints with in-use guard"
```

---

## Task 10: Transactions router (TDD)

Endpoints: `POST /api/transactions`, `GET /api/transactions?month=&category_id=`, `PUT /api/transactions/{id}`, `DELETE /api/transactions/{id}`.

**Files:**
- Create: `backend/app/routers/transactions.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_routes/test_transactions.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_routes/test_transactions.py`:

```python
def test_create_transaction_returns_201(client):
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    response = client.post(
        "/api/transactions",
        json={
            "amount": "12.34",
            "date": "2026-05-10",
            "category_id": cat_id,
            "description": "Milk",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == "12.34"
    assert body["date"] == "2026-05-10"
    assert body["description"] == "Milk"
    assert body["is_recurring"] is False


def test_create_recurring_transaction_seeds_schedule(client, db_session):
    from app.services import recurring_service
    cat_id = client.post("/api/categories", json={"name": "Rent"}).json()["id"]
    client.post(
        "/api/transactions",
        json={
            "amount": "500.00",
            "date": "2026-05-01",
            "category_id": cat_id,
            "description": "Rent",
            "is_recurring": True,
        },
    )
    schedules = recurring_service.list_schedules(db_session, user_id=1)
    assert len(schedules) == 1
    assert schedules[0].next_occurrence_date.isoformat() == "2026-06-01"


def test_create_transaction_rejects_unknown_category(client):
    response = client.post(
        "/api/transactions",
        json={"amount": "5", "date": "2026-05-10", "category_id": 999, "description": ""},
    )
    assert response.status_code == 404


def test_create_transaction_rejects_zero_amount(client):
    cat_id = client.post("/api/categories", json={"name": "Misc"}).json()["id"]
    response = client.post(
        "/api/transactions",
        json={"amount": "0", "date": "2026-05-10", "category_id": cat_id, "description": ""},
    )
    assert response.status_code == 422


def test_list_transactions_filters_by_month_and_category(client):
    g = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    r = client.post("/api/categories", json={"name": "Rent"}).json()["id"]
    client.post("/api/transactions", json={"amount": "1", "date": "2026-04-30", "category_id": g, "description": "old"})
    client.post("/api/transactions", json={"amount": "5", "date": "2026-05-03", "category_id": g, "description": "food"})
    client.post("/api/transactions", json={"amount": "500", "date": "2026-05-01", "category_id": r, "description": "rent"})

    response = client.get("/api/transactions", params={"month": "2026-05"})
    assert response.status_code == 200
    descs = [t["description"] for t in response.json()]
    assert sorted(descs) == ["food", "rent"]

    only_rent = client.get("/api/transactions", params={"month": "2026-05", "category_id": r}).json()
    assert [t["description"] for t in only_rent] == ["rent"]


def test_update_transaction_returns_200_with_new_values(client):
    cat_id = client.post("/api/categories", json={"name": "Misc"}).json()["id"]
    tx_id = client.post(
        "/api/transactions",
        json={"amount": "5", "date": "2026-05-01", "category_id": cat_id, "description": "old"},
    ).json()["id"]

    response = client.put(
        f"/api/transactions/{tx_id}",
        json={"amount": "9.99", "description": "new"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["amount"] == "9.99"
    assert body["description"] == "new"
    assert body["date"] == "2026-05-01"


def test_update_unknown_transaction_returns_404(client):
    response = client.put("/api/transactions/9999", json={"amount": "1"})
    assert response.status_code == 404


def test_delete_transaction_returns_204(client):
    cat_id = client.post("/api/categories", json={"name": "Misc"}).json()["id"]
    tx_id = client.post(
        "/api/transactions",
        json={"amount": "5", "date": "2026-05-01", "category_id": cat_id, "description": ""},
    ).json()["id"]

    response = client.delete(f"/api/transactions/{tx_id}")
    assert response.status_code == 204

    assert client.get("/api/transactions").json() == []
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_routes/test_transactions.py -v`
Expected: route not mounted → 404s.

- [ ] **Step 3: Implement `backend/app/routers/transactions.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.transaction import TransactionCreate, TransactionRead, TransactionUpdate
from app.services import transaction_service

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return transaction_service.create_transaction(
            db,
            user_id=user_id,
            amount=payload.amount,
            tx_date=payload.date,
            category_id=payload.category_id,
            description=payload.description,
            is_recurring=payload.is_recurring,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    category_id: int | None = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return transaction_service.list_transactions(
        db, user_id=user_id, month=month, category_id=category_id
    )


@router.put("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return transaction_service.update_transaction(
            db,
            user_id=user_id,
            transaction_id=transaction_id,
            amount=payload.amount,
            tx_date=payload.date,
            category_id=payload.category_id,
            description=payload.description,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        transaction_service.delete_transaction(
            db, user_id=user_id, transaction_id=transaction_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
```

- [ ] **Step 4: Mount the router in `backend/app/main.py`**

Update the imports/includes block to:

```python
from app.routers import categories, health, transactions

app.include_router(health.router)
app.include_router(categories.router)
app.include_router(transactions.router)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_routes/test_transactions.py -v`
Expected: 8 passed.

- [ ] **Step 6: Full suite**

Run: `pytest -v`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/transactions.py backend/app/main.py backend/tests/test_routes/test_transactions.py
git commit -m "feat(backend): add transactions REST endpoints with filters and recurring seed"
```

---

## Task 11: Budgets router (TDD)

Endpoints: `PUT /api/budgets/{category_id}` upserts a monthly budget and returns it; `GET /api/budgets?month=YYYY-MM` returns all budgets enriched with `spent`, `over_budget`, `overage`.

**Files:**
- Create: `backend/app/routers/budgets.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_routes/test_budgets.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_routes/test_budgets.py`:

```python
def test_put_budget_returns_200_with_new_limit(client):
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    response = client.put(
        f"/api/budgets/{cat_id}",
        json={"month": "2026-05", "monthly_limit": "200"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category_id"] == cat_id
    assert body["month"] == "2026-05"
    assert body["monthly_limit"] == "200.00"


def test_put_budget_overwrites_existing(client):
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    client.put(f"/api/budgets/{cat_id}", json={"month": "2026-05", "monthly_limit": "200"})
    response = client.put(
        f"/api/budgets/{cat_id}",
        json={"month": "2026-05", "monthly_limit": "250"},
    )
    assert response.status_code == 200
    assert response.json()["monthly_limit"] == "250.00"


def test_put_budget_for_unknown_category_returns_404(client):
    response = client.put(
        "/api/budgets/9999", json={"month": "2026-05", "monthly_limit": "10"}
    )
    assert response.status_code == 404


def test_put_budget_rejects_bad_month(client):
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    response = client.put(
        f"/api/budgets/{cat_id}", json={"month": "2026/05", "monthly_limit": "10"}
    )
    assert response.status_code == 422


def test_get_budgets_returns_spending_and_overage(client):
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    client.put(f"/api/budgets/{cat_id}", json={"month": "2026-05", "monthly_limit": "100"})
    client.post("/api/transactions", json={
        "amount": "60", "date": "2026-05-03", "category_id": cat_id, "description": "food",
    })
    client.post("/api/transactions", json={
        "amount": "70", "date": "2026-05-10", "category_id": cat_id, "description": "more food",
    })

    response = client.get("/api/budgets", params={"month": "2026-05"})
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0] == {
        "category_id": cat_id,
        "category_name": "Groceries",
        "month": "2026-05",
        "monthly_limit": "100.00",
        "spent": "130.00",
        "over_budget": True,
        "overage": "30.00",
    }


def test_get_budgets_for_month_without_budgets_returns_empty(client):
    response = client.get("/api/budgets", params={"month": "2026-05"})
    assert response.status_code == 200
    assert response.json() == []
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_routes/test_budgets.py -v`
Expected: 404s — router not mounted.

- [ ] **Step 3: Implement `backend/app/routers/budgets.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.budget_limit import BudgetRead, BudgetSet, BudgetWithSpending
from app.services import budget_service

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


@router.put("/{category_id}", response_model=BudgetRead)
def set_budget(
    category_id: int,
    payload: BudgetSet,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return budget_service.set_budget(
            db,
            user_id=user_id,
            category_id=category_id,
            month=payload.month,
            monthly_limit=payload.monthly_limit,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("", response_model=list[BudgetWithSpending])
def list_budgets(
    month: str = Query(pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    rows = budget_service.list_budgets_with_spending(db, user_id=user_id, month=month)
    return [
        BudgetWithSpending(
            category_id=r.category_id,
            category_name=r.category_name,
            month=r.month,
            monthly_limit=r.monthly_limit,
            spent=r.spent,
            over_budget=r.over_budget,
            overage=r.overage,
        )
        for r in rows
    ]
```

- [ ] **Step 4: Mount router in `backend/app/main.py`**

Update imports/include block to:

```python
from app.routers import budgets, categories, health, transactions

app.include_router(health.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_routes/test_budgets.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/budgets.py backend/app/main.py backend/tests/test_routes/test_budgets.py
git commit -m "feat(backend): add budgets REST endpoints with spending/overage rollup"
```

---

## Task 12: CSV export router (TDD)

Endpoint: `GET /api/export/csv?month=YYYY-MM` returns `Content-Type: text/csv` and a download-friendly filename.

**Files:**
- Create: `backend/app/routers/export.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_routes/test_export.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_routes/test_export.py`:

```python
def test_export_csv_returns_csv_content_type_and_header(client):
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    client.post("/api/transactions", json={
        "amount": "12.34", "date": "2026-05-10", "category_id": cat_id, "description": "Milk",
    })

    response = client.get("/api/export/csv", params={"month": "2026-05"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert "2026-05" in response.headers["content-disposition"]

    body = response.text.splitlines()
    assert body[0] == "date,category,description,amount"
    assert body[1] == "2026-05-10,Groceries,Milk,12.34"


def test_export_csv_without_month_returns_all(client):
    cat_id = client.post("/api/categories", json={"name": "Misc"}).json()["id"]
    client.post("/api/transactions", json={
        "amount": "1.00", "date": "2026-04-30", "category_id": cat_id, "description": "april",
    })
    client.post("/api/transactions", json={
        "amount": "2.00", "date": "2026-05-01", "category_id": cat_id, "description": "may",
    })

    response = client.get("/api/export/csv")
    assert response.status_code == 200
    lines = response.text.splitlines()
    assert len(lines) == 3  # header + 2 rows


def test_export_csv_rejects_bad_month(client):
    response = client.get("/api/export/csv", params={"month": "bad"})
    assert response.status_code == 422
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_routes/test_export.py -v`
Expected: 404s.

- [ ] **Step 3: Implement `backend/app/routers/export.py`**

```python
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.services import export_service

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/csv")
def export_csv(
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    csv_text = export_service.export_transactions_csv(db, user_id=user_id, month=month)
    filename_part = month if month else "all"
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="transactions-{filename_part}.csv"'
        },
    )
```

- [ ] **Step 4: Mount router in `backend/app/main.py`**

Update imports/include block to:

```python
from app.routers import budgets, categories, export, health, transactions

app.include_router(health.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(export.router)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_routes/test_export.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/export.py backend/app/main.py backend/tests/test_routes/test_export.py
git commit -m "feat(backend): add CSV export endpoint"
```

---

## Task 13: CORS, end-to-end smoke test, README polish

The React dev server (Phase 2) will live on http://localhost:3000 and call this API on http://localhost:8000 — we need CORS in place now so Phase 2 doesn't get blocked. Also runs one final integration test that exercises every endpoint in sequence.

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_routes/test_smoke_e2e.py`
- Modify: `README.md`

- [ ] **Step 1: Write the end-to-end smoke test**

Create `backend/tests/test_routes/test_smoke_e2e.py`:

```python
def test_full_user_flow(client):
    # 1. Health
    assert client.get("/api/health").json() == {"status": "ok"}

    # 2. Create categories
    groceries = client.post("/api/categories", json={"name": "Groceries"}).json()
    rent = client.post("/api/categories", json={"name": "Rent"}).json()
    assert {c["name"] for c in client.get("/api/categories").json()} == {"Groceries", "Rent"}

    # 3. Create transactions (one recurring)
    client.post("/api/transactions", json={
        "amount": "12.34", "date": "2026-05-10",
        "category_id": groceries["id"], "description": "Milk",
    })
    client.post("/api/transactions", json={
        "amount": "500.00", "date": "2026-05-01",
        "category_id": rent["id"], "description": "Rent", "is_recurring": True,
    })

    listed = client.get("/api/transactions", params={"month": "2026-05"}).json()
    assert len(listed) == 2

    # 4. Set a budget that gets blown
    client.put(f"/api/budgets/{groceries['id']}",
               json={"month": "2026-05", "monthly_limit": "10"})
    budgets = client.get("/api/budgets", params={"month": "2026-05"}).json()
    assert budgets[0]["over_budget"] is True

    # 5. Export
    csv_resp = client.get("/api/export/csv", params={"month": "2026-05"})
    assert csv_resp.status_code == 200
    assert "Milk" in csv_resp.text
    assert "Rent" in csv_resp.text

    # 6. Delete one transaction
    tx_id = listed[0]["id"]
    assert client.delete(f"/api/transactions/{tx_id}").status_code == 204
    assert len(client.get("/api/transactions", params={"month": "2026-05"}).json()) == 1


def test_cors_preflight_allows_localhost_3000(client):
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
```

- [ ] **Step 2: Run to verify CORS test fails**

Run: `pytest tests/test_routes/test_smoke_e2e.py -v`
Expected: `test_full_user_flow` passes, `test_cors_preflight_allows_localhost_3000` fails (no CORS yet).

- [ ] **Step 3: Add CORS middleware in `backend/app/main.py`**

After `app = FastAPI(...)` add:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 4: Run smoke test**

Run: `pytest tests/test_routes/test_smoke_e2e.py -v`
Expected: both pass.

- [ ] **Step 5: Run the whole suite with coverage**

Run: `pytest --cov=app --cov-report=term-missing`
Expected: all tests pass; service modules report ≥80% coverage.

- [ ] **Step 6: Expand `README.md`**

Replace `README.md` with:

```markdown
# Financial Assistant

Personal finance tracker — single user, local-first. Phase 1 ships a FastAPI backend; Phase 2 adds a React frontend.

## Backend (Phase 1)

### Stack
- Python 3.10+, FastAPI, SQLAlchemy 2.0, SQLite

### Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

### Run

```powershell
uvicorn app.main:app --reload --port 8000
```

- Interactive docs: http://localhost:8000/docs
- Health check:   http://localhost:8000/api/health

### Endpoints

| Method | Path                               | Purpose                          |
|--------|------------------------------------|----------------------------------|
| GET    | /api/health                        | Service status                   |
| GET    | /api/categories                    | List categories                  |
| POST   | /api/categories                    | Create category                  |
| DELETE | /api/categories/{id}               | Delete (409 if in use)           |
| GET    | /api/transactions?month&category_id| List, filtered                   |
| POST   | /api/transactions                  | Create (auto-seeds recurring)    |
| PUT    | /api/transactions/{id}             | Update                           |
| DELETE | /api/transactions/{id}             | Delete                           |
| PUT    | /api/budgets/{category_id}         | Upsert monthly limit             |
| GET    | /api/budgets?month                 | Budgets + spent + overage        |
| GET    | /api/export/csv?month              | Download CSV                     |

### Tests

```powershell
pytest
pytest --cov=app --cov-report=term-missing
```

### Recurring transactions

When a transaction is created with `is_recurring: true`, a `RecurringSchedule` is seeded with `next_occurrence_date = date + 1 month`. On app startup the lifespan hook materializes every overdue schedule, generating real transactions until the schedule's next occurrence sits in the future.

## Frontend (Phase 2)

Coming next.
```

- [ ] **Step 7: Final commit**

```bash
git add backend/app/main.py backend/tests/test_routes/test_smoke_e2e.py README.md
git commit -m "feat(backend): add CORS, end-to-end smoke test and backend README"
```

---

## Done criteria for Phase 1

- `pytest` (from `backend/`) reports all green.
- `uvicorn app.main:app --reload --port 8000` starts cleanly; `/docs` renders the OpenAPI UI showing every endpoint in the table above.
- Creating a recurring transaction with a past start date materializes catch-up transactions automatically on the next `uvicorn` restart.
- A SQLite file `backend/financial.db` is created on first run and persists data across restarts.
