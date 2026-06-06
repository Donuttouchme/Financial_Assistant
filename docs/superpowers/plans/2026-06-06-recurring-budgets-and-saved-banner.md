# Recurring Budgets + Theme-Aware Saved Banner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make budgets "set once, applies forward" while preserving historical accuracy, and fix the Saved-and-add-another banner to read correctly in all six themes. Ship as v1.3.3.

**Architecture:** Reinterpret existing `budget_limits.month` column as **effective_month**: the limit applies from that month onward until a later row for the same `(user_id, category_id)` supersedes it. The PUT endpoint stamps the current real-world month server-side via an injectable clock dependency. The GET lookup picks the most-recent row at-or-before the queried month per category. No DB schema change; no frontend type rename. The Saved banner swaps hardcoded emerald shades for `bg-primary/10 text-foreground border border-primary/30`, which adapts to every theme through the `--primary` and `--foreground` CSS variables already defined in `frontend/src/index.css`.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + pydantic v2 + SQLite (backend); React 18 + TanStack Query 5 + shadcn-ui + Vitest 2 + MSW 2 (frontend); pytest + pytest-asyncio (backend tests).

**Spec:** `docs/superpowers/specs/2026-06-06-recurring-budgets-and-saved-banner-design.md`

---

## File Map

**Backend:**
- Modify: `backend/app/dependencies.py` — add `get_current_month()` clock dep.
- Modify: `backend/app/models/budget_limit.py` — add docstring.
- Modify: `backend/app/schemas/budget_limit.py` — drop `month` from `BudgetSet`.
- Modify: `backend/app/services/budget_service.py` — rewrite `set_budget` and `list_budgets_with_spending`.
- Modify: `backend/app/routers/budgets.py` — wire `get_current_month()` into `set_budget`.
- Modify: `backend/app/main.py` — version bump to 1.3.3.
- Create: `backend/tests/test_budgets_recurring.py` — new service-level timeline tests.
- Modify: `backend/tests/test_routes/test_budgets.py` — adapt to new payload shape.

**Frontend:**
- Modify: `frontend/src/api/types.ts` — drop `month` from `BudgetSetPayload`.
- Modify: `frontend/src/api/budgets.ts` — no signature change, just consume new payload.
- Modify: `frontend/src/hooks/queries/useBudgets.ts` — already pass payload through; verify only.
- Modify: `frontend/src/components/budgets/BudgetsTable.tsx` — drop `month` from mutation payload.
- Modify: `frontend/src/pages/BudgetsPage.tsx` — add helper sentence under heading.
- Modify: `frontend/src/components/transactions/TransactionFormDialog.tsx` — theme-aware Saved banner.
- Modify: `frontend/src/tests/handlers.ts` — MSW PUT handler: drop `month` requirement, default the stored row's month to a fixed test value.
- Modify: `frontend/src/components/budgets/__tests__/BudgetsTable.test.tsx` — adapt to new payload.
- Modify: `frontend/package.json` — version bump to 1.3.3.

**Release:**
- Modify: `scripts/installer.iss` — `MyAppVersion` to 1.3.3.
- Build artifact: `dist/Financial-Assistant-Setup-v1.3.3.exe`.
- GH release: tag `v1.3.3`.

---

## Task 1: Add `get_current_month()` clock dependency

**Files:**
- Modify: `backend/app/dependencies.py`
- Test: covered indirectly by Task 4 router test; no separate unit test for the helper (it's a one-line wrapper around `datetime.utcnow()`).

- [ ] **Step 1: Add helper to dependencies.py**

Append to `backend/app/dependencies.py`:

```python
from datetime import datetime, timezone


def get_current_month() -> str:
    """Return today's UTC month as 'YYYY-MM'.

    Injected as a FastAPI dependency so tests can override it via
    ``app.dependency_overrides[get_current_month]`` and pin behavior to a
    known calendar month without monkey-patching the clock.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m")
```

- [ ] **Step 2: Sanity-check imports & run a quick smoke**

Run: `cd backend && & ".venv/Scripts/python.exe" -c "from app.dependencies import get_current_month; print(get_current_month())"`
Expected: prints today's YYYY-MM (e.g. `2026-06`).

- [ ] **Step 3: Commit**

```bash
git add backend/app/dependencies.py
git commit -m "feat(budgets): add get_current_month clock dep for v1.3.3 recurring model"
```

---

## Task 2: Update model docstring + schema

**Files:**
- Modify: `backend/app/models/budget_limit.py`
- Modify: `backend/app/schemas/budget_limit.py`

- [ ] **Step 1: Add docstring on `BudgetLimit`**

Replace the class definition in `backend/app/models/budget_limit.py` (line 9 onward) with:

```python
class BudgetLimit(Base):
    """Per-category monthly spending limit, applied as a recurring rule.

    The ``month`` column is the **effective-from** month for this limit:
    the limit applies to that month and every later month until a row for
    the same ``(user_id, category_id)`` with a later ``month`` supersedes
    it. Lookup: pick the row with the largest ``month`` value at-or-before
    the queried month.

    Example: a row with month='2026-06', monthly_limit=500 means "Groceries
    is 500 from June 2026 onward." Adding a row month='2026-09',
    monthly_limit=600 changes the effective limit to 600 for Sep 2026+;
    Jun/Jul/Aug still resolve to 500.
    """

    __tablename__ = "budget_limits"
    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "month", name="uq_budget_user_cat_month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # effective-from YYYY-MM
    monthly_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
```

- [ ] **Step 2: Drop `month` from `BudgetSet`**

Replace `BudgetSet` in `backend/app/schemas/budget_limit.py`:

```python
class BudgetSet(BaseModel):
    """PUT /api/budgets/{category_id} request body.

    The server stamps the effective-from month from the request clock; the
    client cannot set it. Keeps the recurring-budget mental model clean.
    """
    monthly_limit: Decimal = Field(ge=Decimal("0"))
```

Leave `BudgetRead`, `BudgetWithSpending`, and `BudgetWithSpendingRow` unchanged.

- [ ] **Step 3: Run backend tests to see expected breakage**

Run: `cd backend && & ".venv/Scripts/python.exe" -m pytest tests/test_routes/test_budgets.py -q`
Expected: multiple failures with `unexpected keyword argument 'month'` or 422 status mismatches. These will be fixed in Task 5.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/budget_limit.py backend/app/schemas/budget_limit.py
git commit -m "refactor(budgets): document recurring semantics + drop month from BudgetSet"
```

---

## Task 3: Rewrite `set_budget` service signature

**Files:**
- Modify: `backend/app/services/budget_service.py:34-65`

- [ ] **Step 1: Replace `set_budget` function**

In `backend/app/services/budget_service.py`, replace the `set_budget` function (lines 34-65) with:

```python
def set_budget(
    db: Session,
    *,
    user_id: int,
    category_id: int,
    effective_month: str,
    monthly_limit: Decimal,
) -> BudgetLimit:
    """Set the recurring limit for ``category_id``, effective from ``effective_month``.

    If a row already exists at exactly this effective_month, its limit is
    overwritten. Older rows are preserved (history); newer rows still
    supersede this one for their months.
    """
    _validate_month(effective_month)
    _ensure_expense_category(db, user_id=user_id, category_id=category_id)
    monthly_limit = monthly_limit.quantize(Decimal("0.01"))

    existing = db.execute(
        select(BudgetLimit).where(
            BudgetLimit.user_id == user_id,
            BudgetLimit.category_id == category_id,
            BudgetLimit.month == effective_month,
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.monthly_limit = monthly_limit
        db.commit()
        db.refresh(existing)
        return existing

    budget = BudgetLimit(
        user_id=user_id,
        category_id=category_id,
        month=effective_month,
        monthly_limit=monthly_limit,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget
```

Only change from the old function: parameter renamed from `month` to `effective_month`. Body is identical apart from the variable name. The DB column is still `month`.

- [ ] **Step 2: No test run yet — Task 4 wires the router and Task 5 fixes the tests.**

Defer test run until Task 5.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/budget_service.py
git commit -m "refactor(budgets): rename set_budget param to effective_month"
```

---

## Task 4: Wire `get_current_month()` into the budgets router

**Files:**
- Modify: `backend/app/routers/budgets.py`

- [ ] **Step 1: Replace the router file**

Overwrite `backend/app/routers/budgets.py` with:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_month, get_current_user_id
from app.schemas.budget_limit import BudgetRead, BudgetSet, BudgetWithSpending
from app.services import budget_service

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


@router.put("/{category_id}", response_model=BudgetRead)
def set_budget(
    category_id: int,
    payload: BudgetSet,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    current_month: str = Depends(get_current_month),
):
    """Set Groceries=X effective from the current calendar month forward.

    The effective month is server-stamped — not client-provided — so a
    misbehaving client can't silently rewrite past history.
    """
    try:
        return budget_service.set_budget(
            db,
            user_id=user_id,
            category_id=category_id,
            effective_month=current_month,
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

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/budgets.py
git commit -m "feat(budgets): server-stamp effective_month via clock dep"
```

---

## Task 5: Update existing budget route tests to new payload shape

**Files:**
- Modify: `backend/tests/test_routes/test_budgets.py`
- Modify: `backend/tests/conftest.py` (only if a fresh fixture is needed; see Step 1)

- [ ] **Step 1: Add a clock-override fixture**

Append to `backend/tests/conftest.py` (after the `client` fixture):

```python
from app.dependencies import get_current_month


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
```

- [ ] **Step 2: Replace `backend/tests/test_routes/test_budgets.py` with the v1.3.3 shape**

```python
def test_put_budget_returns_200_with_new_limit(client, freeze_month):
    freeze_month("2026-05")
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    response = client.put(
        f"/api/budgets/{cat_id}",
        json={"monthly_limit": "200"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category_id"] == cat_id
    assert body["month"] == "2026-05"
    assert body["monthly_limit"] == "200.00"


def test_put_budget_overwrites_existing_in_same_month(client, freeze_month):
    freeze_month("2026-05")
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    client.put(f"/api/budgets/{cat_id}", json={"monthly_limit": "200"})
    response = client.put(
        f"/api/budgets/{cat_id}",
        json={"monthly_limit": "250"},
    )
    assert response.status_code == 200
    assert response.json()["monthly_limit"] == "250.00"


def test_put_budget_rejects_month_in_payload(client, freeze_month):
    freeze_month("2026-05")
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    response = client.put(
        f"/api/budgets/{cat_id}",
        json={"month": "2026-05", "monthly_limit": "200"},
    )
    # BudgetSet has model_config defaulting to extra='ignore' (pydantic v2
    # default), so the field is silently dropped, not 422'd. The row still
    # gets effective_month=2026-05 from the clock fixture. Assert that
    # silent-drop is the behaviour we get.
    assert response.status_code == 200
    assert response.json()["month"] == "2026-05"


def test_put_budget_for_unknown_category_returns_404(client, freeze_month):
    freeze_month("2026-05")
    response = client.put("/api/budgets/9999", json={"monthly_limit": "10"})
    assert response.status_code == 404


def test_get_budgets_returns_spending_and_overage(client, freeze_month):
    freeze_month("2026-05")
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    client.put(f"/api/budgets/{cat_id}", json={"monthly_limit": "100"})
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


def test_put_budget_on_income_category_returns_400(client, freeze_month):
    freeze_month("2026-05")
    cat_id = client.post(
        "/api/categories", json={"name": "Salary", "kind": "income"}
    ).json()["id"]
    response = client.put(
        f"/api/budgets/{cat_id}",
        json={"monthly_limit": "1000"},
    )
    assert response.status_code == 400
    assert "expense" in response.json()["detail"].lower()
```

This file replaces the old one (drop `test_put_budget_rejects_bad_month` — the field no longer exists). The new `test_put_budget_rejects_month_in_payload` pins the silent-drop behavior.

- [ ] **Step 3: Run these tests**

Run: `cd backend && & ".venv/Scripts/python.exe" -m pytest tests/test_routes/test_budgets.py -v`
Expected: 7 passing. (The forecast lookup logic isn't tested yet — Task 6 covers it.)

- [ ] **Step 4: Commit**

```bash
git add backend/tests/conftest.py backend/tests/test_routes/test_budgets.py
git commit -m "test(budgets): adapt route tests to server-stamped effective_month"
```

---

## Task 6: Rewrite `list_budgets_with_spending` for recurring lookup (TDD)

**Files:**
- Create: `backend/tests/test_budgets_recurring.py` (new, service-level)
- Modify: `backend/app/services/budget_service.py` (`list_budgets_with_spending`)

- [ ] **Step 1: Write the failing timeline tests**

Create `backend/tests/test_budgets_recurring.py`:

```python
"""Service-level tests for the recurring-budget lookup semantics introduced in v1.3.3.

These tests bypass the router so they can plant rows with arbitrary
effective_month values directly in the DB, simulating a multi-month
edit history without juggling the clock dependency.
"""
from decimal import Decimal

import pytest

from app.models.budget_limit import BudgetLimit
from app.models.category import Category
from app.services import budget_service, settings_service


@pytest.fixture
def groceries_cat(db_session):
    cat = Category(user_id=1, name="Groceries", kind="expense")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


def _plant(db, *, cat_id: int, effective_month: str, limit: str) -> None:
    db.add(
        BudgetLimit(
            user_id=1,
            category_id=cat_id,
            month=effective_month,
            monthly_limit=Decimal(limit),
        )
    )
    db.commit()


def test_later_month_returns_most_recent_at_or_before(db_session, groceries_cat):
    settings_service.set_base_currency(db_session, "EUR")
    _plant(db_session, cat_id=groceries_cat.id, effective_month="2026-05", limit="500")
    _plant(db_session, cat_id=groceries_cat.id, effective_month="2026-09", limit="600")

    # May: only the 500 row is effective.
    rows = budget_service.list_budgets_with_spending(
        db_session, user_id=1, month="2026-05"
    )
    assert len(rows) == 1
    assert rows[0].monthly_limit == Decimal("500.00")

    # June, July, August: still 500 (the Sep row hasn't kicked in).
    for m in ("2026-06", "2026-07", "2026-08"):
        rows = budget_service.list_budgets_with_spending(
            db_session, user_id=1, month=m
        )
        assert len(rows) == 1, m
        assert rows[0].monthly_limit == Decimal("500.00"), m

    # September onward: 600.
    for m in ("2026-09", "2026-10", "2027-03"):
        rows = budget_service.list_budgets_with_spending(
            db_session, user_id=1, month=m
        )
        assert len(rows) == 1, m
        assert rows[0].monthly_limit == Decimal("600.00"), m


def test_month_before_any_effective_row_returns_no_row(db_session, groceries_cat):
    settings_service.set_base_currency(db_session, "EUR")
    _plant(db_session, cat_id=groceries_cat.id, effective_month="2026-06", limit="500")

    rows = budget_service.list_budgets_with_spending(
        db_session, user_id=1, month="2026-03"
    )
    assert rows == []


def test_distinct_categories_have_independent_timelines(db_session):
    settings_service.set_base_currency(db_session, "EUR")
    grok = Category(user_id=1, name="Groceries", kind="expense")
    rent = Category(user_id=1, name="Rent", kind="expense")
    db_session.add_all([grok, rent])
    db_session.commit()

    _plant(db_session, cat_id=grok.id, effective_month="2026-01", limit="500")
    _plant(db_session, cat_id=rent.id, effective_month="2026-06", limit="1200")

    rows = budget_service.list_budgets_with_spending(
        db_session, user_id=1, month="2026-03"
    )
    # Only Groceries is effective in March.
    assert len(rows) == 1
    assert rows[0].category_name == "Groceries"

    rows = budget_service.list_budgets_with_spending(
        db_session, user_id=1, month="2026-07"
    )
    by_name = {r.category_name: r for r in rows}
    assert by_name["Groceries"].monthly_limit == Decimal("500.00")
    assert by_name["Rent"].monthly_limit == Decimal("1200.00")


def test_spending_against_recurring_limit(db_session, groceries_cat):
    """Spending is summed for the queried month; limit comes from the most
    recent effective row. Confirms FX-and-aggregation path still works."""
    from datetime import date as _d

    from app.models.transaction import Transaction

    settings_service.set_base_currency(db_session, "EUR")
    _plant(db_session, cat_id=groceries_cat.id, effective_month="2026-01", limit="100")

    db_session.add_all([
        Transaction(
            user_id=1,
            amount=Decimal("60"),
            currency="EUR",
            date=_d(2026, 5, 3),
            category_id=groceries_cat.id,
            description="food",
            is_recurring=False,
        ),
        Transaction(
            user_id=1,
            amount=Decimal("70"),
            currency="EUR",
            date=_d(2026, 5, 10),
            category_id=groceries_cat.id,
            description="more food",
            is_recurring=False,
        ),
    ])
    db_session.commit()

    rows = budget_service.list_budgets_with_spending(
        db_session, user_id=1, month="2026-05"
    )
    assert len(rows) == 1
    assert rows[0].spent == Decimal("130.00")
    assert rows[0].monthly_limit == Decimal("100.00")
    assert rows[0].over_budget is True
    assert rows[0].overage == Decimal("30.00")
```

- [ ] **Step 2: Run them — they should all fail**

Run: `cd backend && & ".venv/Scripts/python.exe" -m pytest tests/test_budgets_recurring.py -v`
Expected: failures. The current `list_budgets_with_spending` filters with `BudgetLimit.month == month` so the "May returns 500 even though only Jan row exists" expectation fails for the timeline tests; the income filter is fine but counts wrong.

- [ ] **Step 3: Rewrite `list_budgets_with_spending`**

Replace the body of `list_budgets_with_spending` in `backend/app/services/budget_service.py` (lines 76 onward) with:

```python
def list_budgets_with_spending(
    db: Session, *, user_id: int, month: str
) -> list[BudgetWithSpendingRow]:
    from sqlalchemy import case
    from app.models.fx_rate import FxRate
    from app.services import settings_service

    _validate_month(month)
    start, end = _month_bounds(month)
    base_currency = settings_service.get_settings(db).base_currency

    fx_native = FxRate.__table__.alias("fx_native")
    fx_base = FxRate.__table__.alias("fx_base")

    def _rate_expr(alias, currency_col):
        return case(
            (currency_col == "EUR", Decimal("1.0")),
            else_=alias.c.rate_to_eur,
        )

    base_amount_expr = case(
        (Transaction.currency == base_currency, Transaction.amount),
        (
            (_rate_expr(fx_native, Transaction.currency).is_(None))
            | (_rate_expr(fx_base, base_currency).is_(None)),
            None,
        ),
        else_=Transaction.amount
        * _rate_expr(fx_base, base_currency)
        / _rate_expr(fx_native, Transaction.currency),
    )

    spent_subq = (
        select(
            Transaction.category_id.label("category_id"),
            func.coalesce(func.sum(base_amount_expr), 0).label("spent"),
        )
        .select_from(Transaction)
        .join(
            fx_native,
            (fx_native.c.currency == Transaction.currency)
            & (fx_native.c.date == Transaction.date),
            isouter=True,
        )
        .join(
            fx_base,
            (fx_base.c.currency == base_currency) & (fx_base.c.date == Transaction.date),
            isouter=True,
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.date >= start,
            Transaction.date < end,
        )
        .group_by(Transaction.category_id)
        .subquery()
    )

    # Effective-row picker: per category, take the row with the largest
    # month at-or-before the queried month. Correlated subquery is fine on
    # SQLite and reads cleanly without DB-specific window-function syntax.
    effective_month_subq = (
        select(func.max(BudgetLimit.month))
        .where(
            BudgetLimit.user_id == user_id,
            BudgetLimit.category_id == Category.id,
            BudgetLimit.month <= month,
        )
        .correlate(Category)
        .scalar_subquery()
    )

    rows = db.execute(
        select(BudgetLimit, Category.name, spent_subq.c.spent)
        .join(Category, Category.id == BudgetLimit.category_id)
        .outerjoin(spent_subq, spent_subq.c.category_id == BudgetLimit.category_id)
        .where(
            BudgetLimit.user_id == user_id,
            BudgetLimit.month == effective_month_subq,
        )
    ).all()

    two = Decimal("0.01")
    result: list[BudgetWithSpendingRow] = []
    for budget, cat_name, spent in rows:
        spent_dec = (Decimal(str(spent)) if spent is not None else Decimal("0")).quantize(two)
        limit = budget.monthly_limit.quantize(two)
        overage = (spent_dec - limit).quantize(two) if spent_dec > limit else Decimal("0.00")
        result.append(
            BudgetWithSpendingRow(
                category_id=budget.category_id,
                category_name=cat_name,
                month=budget.month,  # the EFFECTIVE month, not the queried one
                monthly_limit=limit,
                spent=spent_dec,
                over_budget=spent_dec > limit,
                overage=overage,
            )
        )
    return result
```

Key change: rows are filtered by `BudgetLimit.month == (max effective month at-or-before queried month per category)` via a correlated scalar subquery, rather than `BudgetLimit.month == month`. Categories with no row at-or-before the queried month produce no result row.

- [ ] **Step 4: Run the new tests AND the existing route tests**

Run: `cd backend && & ".venv/Scripts/python.exe" -m pytest tests/test_budgets_recurring.py tests/test_routes/test_budgets.py -v`
Expected: all 4 new + 7 existing pass.

- [ ] **Step 5: Run the full backend suite to catch regressions**

Run: `cd backend && & ".venv/Scripts/python.exe" -m pytest -q`
Expected: full pass (count should be ≥ 179, the v1.2.1 baseline, plus the 4 new tests).

- [ ] **Step 6: Commit**

```bash
git add backend/tests/test_budgets_recurring.py backend/app/services/budget_service.py
git commit -m "feat(budgets): recurring lookup picks max effective_month per category"
```

---

## Task 7: Frontend API types + budgets.ts

**Files:**
- Modify: `frontend/src/api/types.ts:57-60`

- [ ] **Step 1: Drop `month` from `BudgetSetPayload`**

In `frontend/src/api/types.ts`, replace:

```typescript
export interface BudgetSetPayload {
  month: string;
  monthly_limit: string;
}
```

with:

```typescript
export interface BudgetSetPayload {
  /** Effective-from month is server-stamped; client only sends the limit. */
  monthly_limit: string;
}
```

Leave `BudgetRead` and `BudgetWithSpending` unchanged — they still carry the `month` field (now interpreted as effective-month) and the renderer doesn't break.

- [ ] **Step 2: No further changes to `frontend/src/api/budgets.ts`** — its signature already uses `BudgetSetPayload`, which is now the smaller object.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/types.ts
git commit -m "refactor(budgets): drop month from BudgetSetPayload (server-stamped)"
```

---

## Task 8: Update `BudgetsTable` mutation + `BudgetsPage` helper text

**Files:**
- Modify: `frontend/src/components/budgets/BudgetsTable.tsx:67-82`
- Modify: `frontend/src/pages/BudgetsPage.tsx`

- [ ] **Step 1: Drop `month` from the mutation payload in `BudgetsTable.tsx`**

Replace `commitEdit` in `frontend/src/components/budgets/BudgetsTable.tsx` (lines 67-82) with:

```tsx
  function commitEdit(categoryId: number) {
    try {
      const cleaned = parseMoneyInput(draft);
      if (Number(cleaned) < 0) throw new Error("negative");
      setBudget.mutate(
        {
          categoryId,
          payload: { monthly_limit: cleaned },
        },
        { onSettled: () => setEditing(null) },
      );
    } catch {
      toast.error("Invalid amount");
      setEditing(null);
    }
  }
```

Only change: the inner `payload` object no longer has `month`. Everything else in the file is untouched. The `month` prop on `BudgetsTable` is still used by `useBudgetsForMonth(month)` and is still needed.

- [ ] **Step 2: Add helper text in `BudgetsPage.tsx`**

Replace `frontend/src/pages/BudgetsPage.tsx` with:

```tsx
import { BudgetsTable } from "@/components/budgets/BudgetsTable";
import { EmptyAppState } from "@/components/EmptyAppState";
import { useUrlMonth } from "@/hooks/useUrlMonth";
import { useCategories } from "@/hooks/queries/useCategories";
import { monthLabel } from "@/lib/date";

export default function BudgetsPage() {
  const { month } = useUrlMonth();
  const { data: cats, isLoading } = useCategories();

  if (!isLoading && (cats?.length ?? 0) === 0) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold">Budgets</h2>
        <EmptyAppState />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold">
          Budgets — {monthLabel(month)}
        </h2>
        <p className="text-sm text-muted-foreground">
          Limits set here apply from the current month forward. Past months keep their original values.
        </p>
      </div>
      <BudgetsTable month={month} />
    </div>
  );
}
```

- [ ] **Step 3: Type-check the frontend**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: clean exit, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/budgets/BudgetsTable.tsx frontend/src/pages/BudgetsPage.tsx
git commit -m "feat(budgets): drop month from mutation payload + recurring helper text"
```

---

## Task 9: Theme-aware Saved banner in TransactionFormDialog

**Files:**
- Modify: `frontend/src/components/transactions/TransactionFormDialog.tsx:208-216`

- [ ] **Step 1: Swap the banner's className**

In `frontend/src/components/transactions/TransactionFormDialog.tsx`, replace lines 208-216:

```tsx
          {savedFlash && (
            <div
              role="status"
              className="flex items-center gap-2 rounded-md bg-emerald-100 dark:bg-emerald-900 px-3 py-2 text-sm"
            >
              <CheckCircle2 className="h-4 w-4" />
              <span>Saved — enter the next one</span>
            </div>
          )}
```

with:

```tsx
          {savedFlash && (
            <div
              role="status"
              className="flex items-center gap-2 rounded-md border border-primary/30 bg-primary/10 text-foreground px-3 py-2 text-sm"
            >
              <CheckCircle2 className="h-4 w-4 text-primary" />
              <span>Saved — enter the next one</span>
            </div>
          )}
```

Why this works for every theme: `--primary` and `--foreground` are defined on every theme block in `frontend/src/index.css`, so the banner stays on-brand under default/dark/cyberpunk/sakura/emerald-dark/navy-light.

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/transactions/TransactionFormDialog.tsx
git commit -m "fix(themes): saved banner uses theme tokens instead of hardcoded emerald"
```

---

## Task 10: Update MSW handler + BudgetsTable test

**Files:**
- Modify: `frontend/src/tests/handlers.ts:225-245` (PUT handler)
- Modify: `frontend/src/components/budgets/__tests__/BudgetsTable.test.tsx`

- [ ] **Step 1: Rewrite the MSW PUT handler**

In `frontend/src/tests/handlers.ts`, replace the PUT handler (lines 225-245) with:

```typescript
  http.put("/api/budgets/:categoryId", async ({ params, request }) => {
    const categoryId = Number(params.categoryId);
    const body = (await request.json()) as { monthly_limit: string };
    // Server-stamps the effective month. Tests can override the stamped
    // value by setting `testState.currentMonth` before driving the UI.
    const effectiveMonth = testState.currentMonth ?? "2026-06";

    const existing = testState.budgets.find(
      (b) => b.category_id === categoryId && b.month === effectiveMonth,
    );
    if (existing) {
      existing.monthly_limit = body.monthly_limit;
      return HttpResponse.json(existing);
    }
    const created: BudgetRead = {
      id: testState.budgets.length + 1,
      category_id: categoryId,
      month: effectiveMonth,
      monthly_limit: body.monthly_limit,
    };
    testState.budgets.push(created);
    return HttpResponse.json(created, { status: 201 });
  }),
```

Then in the `testState` declaration at the top of the same file (around line 15), add a `currentMonth` field:

```typescript
export const testState = {
  categories: [] as Category[],
  transactions: [] as Transaction[],
  budgets: [] as BudgetRead[],
  importPresets: [] as ImportPreset[],
  recurringSchedules: [] as RecurringSchedule[],
  settings: { base_currency: "CHF" } as SettingsRead,
  fxStatus: { latest_date: null, source: "frankfurter.dev", is_fresh: false } as FxStatusRead,
  currentMonth: null as string | null,
  nextCatId: 1,
  nextTxId: 1,
  nextPresetId: 1,
  nextScheduleId: 1,
};
```

And in `resetTestState` add: `testState.currentMonth = null;`

Also adjust the GET handler so a queried month resolves the most recent effective row (mirrors the new backend lookup). Replace the GET handler body's filter (around line 251-253):

```typescript
    const budgets = month
      ? (() => {
          // Per-category latest row at-or-before `month`.
          const byCat = new Map<number, BudgetRead>();
          for (const b of testState.budgets) {
            if (b.month > month) continue;
            const prev = byCat.get(b.category_id);
            if (!prev || prev.month < b.month) byCat.set(b.category_id, b);
          }
          return Array.from(byCat.values());
        })()
      : testState.budgets;
```

- [ ] **Step 2: Verify the existing BudgetsTable test still passes**

The current `frontend/src/components/budgets/__tests__/BudgetsTable.test.tsx` only renders the empty state — it doesn't drive the PUT path and never inspected the payload, so no assertion needs changing. Just confirm it still passes under the rewritten handlers.

- [ ] **Step 3: Run the frontend test suite**

Run: `cd frontend && npm test -- --run`
Expected: all 125 pre-existing tests pass. (If new test files were added in v1.3.0–1.3.2, expect that many; the bar is "the suite passes, no new failures.")

- [ ] **Step 4: Commit**

```bash
git add frontend/src/tests/handlers.ts frontend/src/components/budgets/__tests__/BudgetsTable.test.tsx
git commit -m "test(budgets): mirror server-stamped effective_month in MSW + tests"
```

---

## Task 11: Version bump + full test suites

**Files:**
- Modify: `backend/app/main.py:70`
- Modify: `frontend/package.json` (version field)
- Modify: `scripts/installer.iss` (MyAppVersion line — find it via the file's existing line for v1.3.2)

- [ ] **Step 1: Bump `backend/app/main.py` line 70**

Replace:

```python
app = FastAPI(title="Financial Assistant API", version="1.3.2", lifespan=lifespan)
```

with:

```python
app = FastAPI(title="Financial Assistant API", version="1.3.3", lifespan=lifespan)
```

- [ ] **Step 2: Bump `frontend/package.json`**

Read the file, find `"version": "1.3.2"`, replace with `"version": "1.3.3"`.

- [ ] **Step 3: Bump `scripts/installer.iss`**

Read the file. Find the `#define MyAppVersion "1.3.2"` line and replace `1.3.2` with `1.3.3`. (If the value is wrapped differently — `AppVersion=1.3.2` etc — match whatever format exists; just bump the digits.)

- [ ] **Step 4: Run full backend suite**

Run: `cd backend && & ".venv/Scripts/python.exe" -m pytest -q`
Expected: full pass.

- [ ] **Step 5: Run full frontend suite + production build**

Run sequentially:
- `cd frontend && npm test -- --run` → all tests pass
- `cd frontend && npm run build` → tsc -b clean + vite build emits to `frontend/dist/` with no errors

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py frontend/package.json scripts/installer.iss
git commit -m "chore: bump version to 1.3.3"
```

---

## Task 12: Build installer + publish GitHub release

**Files:**
- Build output: `dist/Financial-Assistant-Setup-v1.3.3.exe`
- Tag: `v1.3.3`

- [ ] **Step 1: Build the installer**

From the repo root:

Run: `.\scripts\package.ps1 -Version "1.3.3"`
Expected: a fresh `dist/Financial-Assistant-Setup-v1.3.3.exe` (~22-25 MB).

- [ ] **Step 2: Write release notes**

Create `dist/release-notes-v1.3.3.md`:

```markdown
## v1.3.3 — Recurring budgets + theme-aware Saved banner

### Fixes
- **Budgets are now recurring.** Setting "Groceries = 500" applies to every later month until you change it. Past months keep the limit they were tracked against — no retroactive rewriting.
- **Saved banner now adapts to every theme.** The "Saved — enter the next one" flash between Save-and-add-another submissions on the Add Transaction dialog was hardcoded green and unreadable under cyberpunk, sakura, emerald, and navy. It now uses theme accent colors.

### Internals
- Backend `PUT /api/budgets/{category_id}` no longer accepts a `month` field; the server stamps the current calendar month server-side.
- Existing budget rows are forward-compatible: the row's `month` becomes its effective-from month under the new lookup. No data migration needed.

### Install
Download `Financial-Assistant-Setup-v1.3.3.exe` and run it. Upgrade auto-replaces any previous version; your data is preserved.
```

- [ ] **Step 3: Push + tag**

Run sequentially:
- `git push origin main`
- `git tag v1.3.3`
- `git push origin v1.3.3`

- [ ] **Step 4: Create the GitHub release as a draft**

Run: `gh release create v1.3.3 --draft --title "v1.3.3 — Recurring budgets + theme-aware Saved banner" --notes-file dist/release-notes-v1.3.3.md dist/Financial-Assistant-Setup-v1.3.3.exe`
Expected: a draft release URL prints.

- [ ] **Step 5: Publish**

Run: `gh release edit v1.3.3 --draft=false --latest`
Expected: success; release is now public.

- [ ] **Step 6: Final commit (release notes only)**

If `dist/release-notes-v1.3.3.md` should be tracked (check git status; the existing v1.3.2 release notes pattern suggests yes):

```bash
git add dist/release-notes-v1.3.3.md
git commit -m "chore: v1.3.3 release notes"
git push origin main
```

---

## Final verification checklist

- [ ] Backend test suite passes (`cd backend && & ".venv/Scripts/python.exe" -m pytest -q`).
- [ ] Frontend test suite passes (`cd frontend && npm test -- --run`).
- [ ] Frontend production build succeeds (`cd frontend && npm run build`).
- [ ] Installer file present at `dist/Financial-Assistant-Setup-v1.3.3.exe`.
- [ ] `git status` clean (or only lockfile churn).
- [ ] GitHub release `v1.3.3` is public and `--latest`.
- [ ] Tag `v1.3.3` points at the release commit.

## Notes for the implementer

- Always invoke the backend venv as `& ".venv/Scripts/python.exe"` from `backend/` to avoid PowerShell + bash path mangling — there's a memory entry about this.
- If the production build (`npm run build`) reports `Cannot find name 'describe'` etc. in new test files, those files need `import { describe, it, expect } from "vitest"` at the top — tsc -b is stricter than the test runner.
- Use `127.0.0.1`, not `localhost`, if any PowerShell `Invoke-WebRequest` is needed against the running backend (there's a memory entry about IPv6 timeout pitfalls on this machine).
