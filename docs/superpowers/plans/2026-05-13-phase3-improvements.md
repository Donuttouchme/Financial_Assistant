# Phase 3 Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship five Phase 3 improvements: redesigned per-category Budget widget on the dashboard; a Savings transaction-type with goal tracking; a Sakura theme as a third option alongside light/dark; a real page title + Swiss-franc favicon; a CSV import flow with saveable per-bank presets.

**Architecture:** Schema-touching work runs first (Section A — Savings) so the data model is final before later sections build UI on it. Sections B (Budget widget), C (Icon/Title), D (Sakura theme) are frontend-only refactors and can run in any order after A. Section E (CSV import) is self-contained — new backend tables, new routes, new pages — and ships last because its tests rely on the final transaction/category model.

**Tech Stack:** Backend: Python 3.14 · FastAPI · SQLAlchemy 2.0 (Mapped/mapped_column) · Pydantic v2 · SQLite. Frontend: Vite 5 · React 18 · TypeScript strict · Tailwind v3 · shadcn-ui (vendored) · TanStack Query 5 · React Router 6 · react-hook-form 7 · zod 3 · date-fns 3 · sonner 1 · Recharts. Tests: pytest (backend) · Vitest 2 + msw 2 + jsdom 25 (frontend).

---

## Spec recap (from grilling, 2026-05-13)

- **Savings:** third `Category.kind` value `savings`; goal lives on the category itself (nullable `target_amount`, `target_date`); withdrawals allowed via negative transaction amounts; TransactionFormDialog gets a Deposit/Withdraw toggle when the picked category is `kind=savings`; donut and budgets remain expense-only (already enforced); dashboard gets a `Saved` KPI card and a goal-cards row.
- **Budget widget:** dashboard list of every budgeted category with progress bar, sorted by `% used` desc, color-coded (<80% green, 80–99% yellow, ≥100% red). Top-line aggregate. Replaces the old `OverBudgetAlerts` section entirely. Categories without a budget are hidden.
- **Icon + title:** `<title>Financial Assistant</title>`; favicon is an SVG of `Fr.` in a circle, theme-adaptive via `currentColor`.
- **Sakura theme:** third option in `useTheme`, persisted as `fa-theme = 'sakura'`. Palette = Sakura Bloom (deep plum bg HSL 290 30% 8% · cherry primary HSL 340 65% 68% · chart palette in pink/lavender/rose/peach/iris). 3-segment header toggle `[🌸][☀][🌙]`.
- **CSV import:** new `/import` route. Per-bank presets stored as JSON config (`import_presets` table). Supports two amount layouts (single signed column OR debit+credit columns). Configurable delimiter, decimal sep, thousands sep, date format, header-skip rows, column mapping. Help panel with rendered example tables. Preview shows per-row category dropdown (default new auto-created `Imported` category) and bulk-set-category. Duplicate detection by `(user_id, date, |amount|, description)` — flagged in preview, unticked by default, can be re-ticked to force.

---

## File structure

**Backend — new files:**
- `backend/app/migrations.py` — idempotent column-add helper invoked from `lifespan`
- `backend/app/models/import_preset.py`
- `backend/app/schemas/import_preset.py`
- `backend/app/schemas/csv_import.py`
- `backend/app/services/import_preset_service.py`
- `backend/app/services/csv_import_service.py`
- `backend/app/routers/import_presets.py`
- `backend/app/routers/csv_import.py`
- `backend/tests/test_migrations.py`
- `backend/tests/test_import_preset_service.py`
- `backend/tests/test_csv_import_service.py`
- `backend/tests/test_routes/test_import_presets.py`
- `backend/tests/test_routes/test_csv_import.py`

**Backend — modified:**
- `backend/app/models/category.py` (+ `target_amount`, `target_date` cols)
- `backend/app/models/__init__.py` (register `ImportPreset`)
- `backend/app/schemas/category.py` (extend `CategoryKind`, add target fields)
- `backend/app/services/category_service.py` (accept `savings`, pass through target fields)
- `backend/app/main.py` (call `run_migrations`, include new routers)
- `backend/tests/test_category_service.py` (+ savings tests)
- `backend/tests/test_routes/test_categories.py` (+ savings tests)
- `backend/tests/test_transaction_service.py` (+ negative-amount test)

**Frontend — new files:**
- `frontend/public/favicon.svg`
- `frontend/src/components/dashboard/BudgetWidget.tsx`
- `frontend/src/components/dashboard/SavingsGoalCard.tsx`
- `frontend/src/components/dashboard/SavingsGoalsRow.tsx`
- `frontend/src/components/imports/CsvHelpPanel.tsx`
- `frontend/src/components/imports/ImportConfigPanel.tsx`
- `frontend/src/components/imports/ImportPreviewTable.tsx`
- `frontend/src/components/imports/PresetSelector.tsx`
- `frontend/src/api/import-presets.ts`
- `frontend/src/api/csv-import.ts`
- `frontend/src/hooks/queries/useImportPresets.ts`
- `frontend/src/pages/ImportPage.tsx`
- Tests for each component / hook

**Frontend — modified:**
- `frontend/index.html` (title + favicon)
- `frontend/src/index.css` (`.sakura` block)
- `frontend/src/hooks/useTheme.ts` (3-way state)
- `frontend/src/components/layout/ThemeToggle.tsx` (3-segment switch)
- `frontend/src/components/layout/Sidebar.tsx` (Import nav)
- `frontend/src/routes.tsx` (Import route)
- `frontend/src/api/types.ts` (CategoryKind, Category extensions, import types)
- `frontend/src/components/categories/CategoryFormDialog.tsx` (target fields when kind=savings)
- `frontend/src/components/transactions/TransactionFormDialog.tsx` (Deposit/Withdraw toggle)
- `frontend/src/components/dashboard/KpiRow.tsx` (drop Over-budget, add Saved)
- `frontend/src/pages/DashboardPage.tsx` (new sections, replace OverBudgetAlerts)
- `frontend/src/tests/handlers.ts` (handlers for import endpoints)

**Frontend — deleted:**
- `frontend/src/components/dashboard/OverBudgetAlerts.tsx` (replaced by BudgetWidget)
- `frontend/src/components/dashboard/OverBudgetAlerts.test.tsx` (if it exists)

---

# Section A — Savings

## Task 1: Lightweight column-add migration runner

**Files:**
- Create: `backend/app/migrations.py`
- Create: `backend/tests/test_migrations.py`
- Modify: `backend/app/main.py` (call `run_migrations` from `lifespan`)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_migrations.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
import app.models  # noqa: F401
from app.migrations import run_migrations


def _engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


def _columns(eng, table: str) -> list[str]:
    with eng.begin() as conn:
        return [r[1] for r in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()]


def test_run_migrations_is_idempotent(tmp_path):
    eng = _engine()
    run_migrations(eng)
    run_migrations(eng)  # second call must not raise
    cols = _columns(eng, "categories")
    assert "target_amount" in cols
    assert "target_date" in cols


def test_run_migrations_adds_missing_column_on_legacy_db():
    eng = _engine()
    # Simulate a pre-Phase-3 DB by dropping the new columns.
    with eng.begin() as conn:
        conn.exec_driver_sql("ALTER TABLE categories DROP COLUMN target_amount")
        conn.exec_driver_sql("ALTER TABLE categories DROP COLUMN target_date")
    assert "target_amount" not in _columns(eng, "categories")

    run_migrations(eng)
    assert "target_amount" in _columns(eng, "categories")
    assert "target_date" in _columns(eng, "categories")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend; .\.venv\Scripts\Activate.ps1; pytest tests/test_migrations.py -v`
Expected: FAIL — `ModuleNotFoundError: app.migrations` (and the Category model doesn't yet have the columns, so the `DROP COLUMN` is also moot — that's fine for the first run).

- [ ] **Step 3: Write the migration runner**

Create `backend/app/migrations.py`:

```python
"""Lightweight column-add migrations.

We don't use Alembic for this project — the schema additions so far are tiny
nullable columns. This module runs idempotent ALTER TABLE ADD COLUMN statements
on lifespan startup so an existing on-disk SQLite DB (with the wife's real
data) gets upgraded in-place rather than needing a wipe-and-recreate.

Adding a row here adds ONE column. For more complex migrations (renames, type
changes, data backfills) switch to Alembic.
"""
from sqlalchemy import Engine


# (table, column, type_with_null_or_default)
_COLUMN_ADDS: list[tuple[str, str, str]] = [
    ("categories", "target_amount", "NUMERIC(12,2)"),
    ("categories", "target_date", "DATE"),
]


def _existing_columns(conn, table: str) -> set[str]:
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def run_migrations(engine: Engine) -> None:
    with engine.begin() as conn:
        for table, column, ddl in _COLUMN_ADDS:
            if column not in _existing_columns(conn, table):
                conn.exec_driver_sql(
                    f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"
                )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_migrations.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Wire migrations into the FastAPI lifespan**

Modify `backend/app/main.py`, lifespan block:

```python
from app.migrations import run_migrations

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    run_migrations(engine)  # idempotent column-adds for existing DBs
    db = SessionLocal()
    try:
        recurring_service.run_due_schedules(db, today=date.today())
    finally:
        db.close()
    yield
```

- [ ] **Step 6: Run full backend test suite**

Run: `pytest -v`
Expected: 65 prior tests + 2 new migration tests all PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/migrations.py backend/app/main.py backend/tests/test_migrations.py
git commit -m "feat(backend): idempotent ALTER TABLE migration runner on lifespan"
```

---

## Task 2: Add `target_amount` and `target_date` to Category model + schema

**Files:**
- Modify: `backend/app/models/category.py`
- Modify: `backend/app/schemas/category.py`

- [ ] **Step 1: Update the SQLAlchemy model**

Modify `backend/app/models/category.py` — add columns after `kind`:

```python
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_category_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[str] = mapped_column(
        String(16), nullable=False, default="expense", server_default="expense"
    )
    target_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 2: Update the Pydantic schemas**

Modify `backend/app/schemas/category.py`:

```python
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CategoryKind = Literal["income", "expense", "savings"]


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: CategoryKind = "expense"
    target_amount: Decimal | None = Field(default=None, ge=Decimal("0"))
    target_date: date | None = None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: CategoryKind
    target_amount: Decimal | None = None
    target_date: date | None = None
    created_at: datetime
```

- [ ] **Step 3: Run existing test suite to catch incidental breakage**

Run: `pytest -v`
Expected: all 67 tests still PASS (schema additions are backward-compatible — new fields default to None).

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/category.py backend/app/schemas/category.py
git commit -m "feat(backend): Category.target_amount and target_date + savings kind"
```

---

## Task 3: `category_service` accepts `savings` kind and target fields

**Files:**
- Modify: `backend/app/services/category_service.py`
- Modify: `backend/app/routers/categories.py` (plumb new fields)
- Modify: `backend/tests/test_category_service.py`
- Modify: `backend/tests/test_routes/test_categories.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_category_service.py`:

```python
from datetime import date
from decimal import Decimal

import pytest


def test_create_savings_category_accepted(db_session):
    cat = category_service.create_category(
        db_session, user_id=1, name="Pillar 3a", kind="savings"
    )
    assert cat.kind == "savings"
    assert cat.target_amount is None
    assert cat.target_date is None


def test_create_savings_category_with_target(db_session):
    cat = category_service.create_category(
        db_session,
        user_id=1,
        name="Vacation 2027",
        kind="savings",
        target_amount=Decimal("3000.00"),
        target_date=date(2027, 6, 30),
    )
    assert cat.target_amount == Decimal("3000.00")
    assert cat.target_date == date(2027, 6, 30)


def test_create_category_rejects_target_on_expense(db_session):
    with pytest.raises(ValueError, match="target.*savings"):
        category_service.create_category(
            db_session,
            user_id=1,
            name="Groceries",
            kind="expense",
            target_amount=Decimal("100.00"),
        )
```

Append to `backend/tests/test_routes/test_categories.py`:

```python
def test_post_savings_category_with_target(client):
    r = client.post(
        "/api/categories",
        json={
            "name": "Vacation 2027",
            "kind": "savings",
            "target_amount": "3000.00",
            "target_date": "2027-06-30",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["kind"] == "savings"
    assert body["target_amount"] == "3000.00"
    assert body["target_date"] == "2027-06-30"


def test_post_savings_category_without_target(client):
    r = client.post(
        "/api/categories",
        json={"name": "Pillar 3a", "kind": "savings"},
    )
    assert r.status_code == 201
    assert r.json()["target_amount"] is None
    assert r.json()["target_date"] is None


def test_post_target_on_expense_returns_400(client):
    r = client.post(
        "/api/categories",
        json={
            "name": "Groceries",
            "kind": "expense",
            "target_amount": "100.00",
        },
    )
    assert r.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_category_service.py tests/test_routes/test_categories.py -v`
Expected: 6 new tests FAIL (`kind='savings'` rejected by the existing `_VALID_KINDS` tuple).

- [ ] **Step 3: Update the service**

Modify `backend/app/services/category_service.py`:

```python
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category

_VALID_KINDS = ("income", "expense", "savings")


def create_category(
    db: Session,
    *,
    user_id: int,
    name: str,
    kind: str = "expense",
    target_amount: Decimal | None = None,
    target_date: date | None = None,
) -> Category:
    if kind not in _VALID_KINDS:
        raise ValueError(f"kind must be one of {_VALID_KINDS}, got {kind!r}")

    if (target_amount is not None or target_date is not None) and kind != "savings":
        raise ValueError(
            "target_amount / target_date only allowed on savings categories"
        )

    existing = db.execute(
        select(Category).where(Category.user_id == user_id, Category.name == name)
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError(f"Category '{name}' already exists for user {user_id}")

    cat = Category(
        user_id=user_id,
        name=name,
        kind=kind,
        target_amount=target_amount,
        target_date=target_date,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat
```

- [ ] **Step 4: Plumb the fields through the router**

Modify `backend/app/routers/categories.py` — `create_category` handler:

```python
@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return category_service.create_category(
            db,
            user_id=user_id,
            name=payload.name,
            kind=payload.kind,
            target_amount=payload.target_amount,
            target_date=payload.target_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_category_service.py tests/test_routes/test_categories.py -v`
Expected: all PASS.

- [ ] **Step 6: Run full backend suite for regressions**

Run: `pytest -v`
Expected: all 73 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/category_service.py backend/app/routers/categories.py backend/tests/test_category_service.py backend/tests/test_routes/test_categories.py
git commit -m "feat(backend): category_service supports savings kind + targets"
```

---

## Task 4: Negative transaction amount supported (test-only verification)

**Files:**
- Modify: `backend/tests/test_transaction_service.py`

- [ ] **Step 1: Add a withdrawal-style test**

Append to `backend/tests/test_transaction_service.py`:

```python
from datetime import date
from decimal import Decimal

from app.services import category_service, transaction_service


def test_create_transaction_accepts_negative_amount_for_savings(db_session):
    cat = category_service.create_category(
        db_session, user_id=1, name="Emergency", kind="savings"
    )
    tx = transaction_service.create_transaction(
        db_session,
        user_id=1,
        amount=Decimal("-200.00"),
        date=date(2026, 5, 13),
        category_id=cat.id,
        description="Used for car repair",
    )
    assert tx.amount == Decimal("-200.00")


def test_create_transaction_accepts_positive_amount_for_savings(db_session):
    cat = category_service.create_category(
        db_session, user_id=1, name="Vacation 2027", kind="savings"
    )
    tx = transaction_service.create_transaction(
        db_session,
        user_id=1,
        amount=Decimal("500.00"),
        date=date(2026, 5, 13),
        category_id=cat.id,
        description="May deposit",
    )
    assert tx.amount == Decimal("500.00")
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_transaction_service.py -v`
Expected: PASS (the existing `Numeric(12,2)` column accepts negative values; the service has no positive-only guard for savings).

If they fail because `transaction_service` rejects non-positive amounts, REMOVE the rejection only for `kind=savings` — keep the rejection in place for income/expense. Show me the failure before making that change.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_transaction_service.py
git commit -m "test(backend): savings transactions accept positive and negative amounts"
```

---

## Task 5: Frontend API types

**Files:**
- Modify: `frontend/src/api/types.ts`

- [ ] **Step 1: Extend types**

Modify `frontend/src/api/types.ts` — replace the top section:

```ts
export type CategoryKind = "income" | "expense" | "savings";

export interface Category {
  id: number;
  name: string;
  kind: CategoryKind;
  target_amount: string | null;
  target_date: string | null;  // ISO YYYY-MM-DD
  created_at: string;
}

export interface CategoryCreatePayload {
  name: string;
  kind?: CategoryKind;
  target_amount?: string | null;
  target_date?: string | null;
}
```

- [ ] **Step 2: Run frontend type check**

Run: `cd frontend; npx tsc --noEmit`
Expected: type errors in any consumer that doesn't yet account for the new fields. Each will be fixed by later tasks in this section; for now confirm the errors are limited to call sites we plan to change.

- [ ] **Step 3: Run frontend tests**

Run: `npm test`
Expected: existing 30 tests PASS — none of them assert on `target_amount` / `target_date` yet.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/types.ts
git commit -m "feat(frontend): CategoryKind includes savings; Category exposes target fields"
```

---

## Task 6: CategoryFormDialog gets target_amount + target_date when kind=savings

**Files:**
- Modify: `frontend/src/components/categories/CategoryFormDialog.tsx`
- Create or Modify: `frontend/src/components/categories/CategoryFormDialog.test.tsx`

- [ ] **Step 1: Write a render-smoke test for the savings branch**

Either edit the existing test file or create `frontend/src/components/categories/CategoryFormDialog.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CategoryFormDialog } from "./CategoryFormDialog";

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{node}</QueryClientProvider>;
}

describe("CategoryFormDialog", () => {
  it("shows target fields when kind switches to savings", async () => {
    render(wrap(<CategoryFormDialog open onOpenChange={() => {}} />));

    // Initial state: kind=expense, no target fields visible.
    expect(screen.queryByLabelText(/target amount/i)).toBeNull();
    expect(screen.queryByLabelText(/target date/i)).toBeNull();

    // Switch the Select to Savings. We use the Radix combobox role.
    const kindTrigger = screen.getByLabelText(/kind/i);
    fireEvent.click(kindTrigger);
    fireEvent.click(await screen.findByRole("option", { name: /savings/i }));

    expect(screen.getByLabelText(/target amount/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/target date/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- CategoryFormDialog`
Expected: FAIL — there is no "savings" option in the kind Select yet, and no target fields conditionally rendered.

- [ ] **Step 3: Update the dialog**

Replace the contents of `frontend/src/components/categories/CategoryFormDialog.tsx`:

```tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useCreateCategory } from "@/hooks/queries/useCategories";
import { parseChfInput } from "@/lib/currency";

const schema = z
  .object({
    name: z.string().min(1, "Required").max(80),
    kind: z.enum(["income", "expense", "savings"]),
    target_amount: z.string().optional().default(""),
    target_date: z.string().optional().default(""),
  })
  .superRefine((v, ctx) => {
    if (v.kind !== "savings") {
      if (v.target_amount || v.target_date) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["target_amount"],
          message: "Targets only allowed on savings categories",
        });
      }
      return;
    }
    if (v.target_amount) {
      try {
        const n = Number(parseChfInput(v.target_amount));
        if (!(n > 0)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ["target_amount"],
            message: "Must be a positive amount",
          });
        }
      } catch {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["target_amount"],
          message: "Invalid amount",
        });
      }
    }
    if (v.target_date && !/^\d{4}-\d{2}-\d{2}$/.test(v.target_date)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["target_date"],
        message: "YYYY-MM-DD",
      });
    }
  });
type FormValues = z.infer<typeof schema>;

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CategoryFormDialog({ open, onOpenChange }: Props) {
  const create = useCreateCategory();
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", kind: "expense", target_amount: "", target_date: "" },
  });

  const kind = form.watch("kind");

  function onSubmit(values: FormValues) {
    create.mutate(
      {
        name: values.name,
        kind: values.kind,
        target_amount:
          values.kind === "savings" && values.target_amount
            ? parseChfInput(values.target_amount)
            : null,
        target_date:
          values.kind === "savings" && values.target_date
            ? values.target_date
            : null,
      },
      {
        onSuccess: () => {
          form.reset();
          onOpenChange(false);
        },
      },
    );
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) form.reset();
        onOpenChange(o);
      }}
    >
      <DialogContent>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <DialogHeader>
            <DialogTitle>New category</DialogTitle>
          </DialogHeader>

          <div className="space-y-2">
            <Label htmlFor="cat-name">Name</Label>
            <Input id="cat-name" {...form.register("name")} autoFocus />
            {form.formState.errors.name && (
              <p className="text-sm text-destructive">
                {form.formState.errors.name.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="cat-kind">Kind</Label>
            <Select
              value={form.watch("kind")}
              onValueChange={(v) =>
                form.setValue("kind", v as FormValues["kind"], { shouldValidate: true })
              }
            >
              <SelectTrigger id="cat-kind" aria-label="Kind">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="expense">Expense</SelectItem>
                <SelectItem value="income">Income</SelectItem>
                <SelectItem value="savings">Savings</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {kind === "savings" && (
            <>
              <div className="space-y-2">
                <Label htmlFor="cat-target-amount">Target amount (CHF, optional)</Label>
                <Input
                  id="cat-target-amount"
                  placeholder="0.00"
                  {...form.register("target_amount")}
                />
                {form.formState.errors.target_amount && (
                  <p className="text-sm text-destructive">
                    {form.formState.errors.target_amount.message}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="cat-target-date">Target date (optional)</Label>
                <Input
                  id="cat-target-date"
                  type="date"
                  {...form.register("target_date")}
                />
                {form.formState.errors.target_date && (
                  <p className="text-sm text-destructive">
                    {form.formState.errors.target_date.message}
                  </p>
                )}
              </div>
            </>
          )}

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- CategoryFormDialog`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/categories/CategoryFormDialog.tsx frontend/src/components/categories/CategoryFormDialog.test.tsx
git commit -m "feat(frontend): CategoryFormDialog supports savings kind + targets"
```

---

## Task 7: TransactionFormDialog gets Deposit / Withdraw toggle for savings categories

**Files:**
- Modify: `frontend/src/components/transactions/TransactionFormDialog.tsx`
- Create or Modify: corresponding test

- [ ] **Step 1: Write the failing test**

Create or extend `frontend/src/components/transactions/TransactionFormDialog.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TransactionFormDialog } from "./TransactionFormDialog";

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{node}</QueryClientProvider>;
}

describe("TransactionFormDialog savings flow", () => {
  it("shows Deposit/Withdraw toggle when picked category is kind=savings", async () => {
    render(wrap(<TransactionFormDialog mode="create" open onOpenChange={() => {}} />));
    // No toggle visible while no category picked.
    expect(screen.queryByRole("group", { name: /direction/i })).toBeNull();

    // Open category select and pick a savings category (mocked via msw default handlers).
    const trigger = screen.getByLabelText(/category/i);
    fireEvent.click(trigger);
    const opt = await screen.findByRole("option", { name: /vacation 2027 \(savings\)/i });
    fireEvent.click(opt);

    expect(screen.getByRole("group", { name: /direction/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /deposit/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /withdraw/i })).toBeInTheDocument();
  });
});
```

Update `frontend/src/tests/handlers.ts` (msw default state) so the category list includes one savings category for testing — add to the initial state seed:

```ts
// Inside the in-memory state setup, add:
state.categories.push({
  id: 99,
  user_id: 1,
  name: "Vacation 2027",
  kind: "savings",
  target_amount: "3000.00",
  target_date: "2027-06-30",
  created_at: new Date().toISOString(),
});
```

(Adjust to match the actual seed pattern in your handlers.ts — read it first.)

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- TransactionFormDialog`
Expected: FAIL — no Deposit/Withdraw group.

- [ ] **Step 3: Add the toggle to TransactionFormDialog**

Modify `frontend/src/components/transactions/TransactionFormDialog.tsx`. Inside the component (after `const { data: categories } = useCategories();`):

```tsx
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

// ... inside the component:
const selectedCategory = (categories ?? []).find(
  (c) => c.id === form.watch("category_id"),
);
const isSavings = selectedCategory?.kind === "savings";
const direction = form.watch("direction") ?? "deposit";

// extend the schema:
const schema = z.object({
  amount: z.string().min(1, "Required").refine(
    (s) => {
      try {
        const n = Number(parseChfInput(s));
        return n > 0;
      } catch {
        return false;
      }
    },
    "Must be a positive amount",
  ),
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "YYYY-MM-DD"),
  category_id: z.coerce.number().int().positive("Pick a category"),
  description: z.string().max(255).default(""),
  is_recurring: z.boolean().default(false),
  direction: z.enum(["deposit", "withdraw"]).default("deposit"),
});
```

Add the toggle UI between the category select and the description field:

```tsx
{isSavings && (
  <div
    role="group"
    aria-label="Direction"
    className="space-y-2"
  >
    <Label>Direction</Label>
    <ToggleGroup
      type="single"
      value={direction}
      onValueChange={(v) => {
        if (v) form.setValue("direction", v as "deposit" | "withdraw");
      }}
    >
      <ToggleGroupItem value="deposit" aria-label="Deposit">
        ↑ Deposit
      </ToggleGroupItem>
      <ToggleGroupItem value="withdraw" aria-label="Withdraw">
        ↓ Withdraw
      </ToggleGroupItem>
    </ToggleGroup>
  </div>
)}
```

Update `onSubmit` to negate the amount when `isSavings && direction === "withdraw"`:

```tsx
function onSubmit(values: FormValues) {
  let amount = parseChfInput(values.amount);
  if (selectedCategory?.kind === "savings" && values.direction === "withdraw") {
    amount = "-" + amount.replace(/^-/, "");  // ensure single leading minus
  }
  // ... rest unchanged but use the computed `amount`
}
```

When loading in edit mode, infer direction from existing amount sign:

```tsx
// In the useEffect that re-seeds the form on open in edit mode, set
//   direction: parseFloat(props.transaction.amount) < 0 ? "withdraw" : "deposit"
// and store amount as |amount| in the input field so the user sees a positive number.
```

- [ ] **Step 4: Install / verify shadcn ToggleGroup is available**

Check `frontend/src/components/ui/toggle-group.tsx` exists. If not:

```bash
cd frontend; npx shadcn@latest add toggle-group
```

(If shadcn writes to literal `@/components/ui/` rather than resolving the alias — known Phase 2 issue — manually move files into `frontend/src/components/ui/`.)

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test -- TransactionFormDialog`
Expected: PASS.

- [ ] **Step 6: Run full frontend suite**

Run: `npm test`
Expected: 30 prior + 1 new = 31 PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/transactions/TransactionFormDialog.tsx frontend/src/components/transactions/TransactionFormDialog.test.tsx frontend/src/components/ui/toggle-group.tsx frontend/src/tests/handlers.ts
git commit -m "feat(frontend): Deposit/Withdraw toggle for savings transactions"
```

---

## Task 8: KpiRow drops Over-budget, adds Saved

**Files:**
- Modify: `frontend/src/components/dashboard/KpiRow.tsx`
- Modify: associated test if it exists

- [ ] **Step 1: Update KpiRow**

Replace the body of `frontend/src/components/dashboard/KpiRow.tsx` reduce-section and the JSX:

```tsx
const catKindById = new Map((cats ?? []).map((c) => [c.id, c.kind]));
const sums = (txs ?? []).reduce(
  (acc, t) => {
    const kind = catKindById.get(t.category_id);
    const n = Number(t.amount);
    if (kind === "income") acc.income += n;
    else if (kind === "expense") acc.expense += n;
    else if (kind === "savings") acc.saved += n;  // negative = withdrawal
    return acc;
  },
  { income: 0, expense: 0, saved: 0 },
);
const net = sums.income - sums.expense - sums.saved;

return (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
    <StatCard label="Income"  value={formatChf(sums.income)}  emphasis="positive" />
    <StatCard label="Expense" value={formatChf(sums.expense)} emphasis="negative" />
    <StatCard label="Net"     value={formatChf(net)} emphasis={net >= 0 ? "positive" : "negative"} />
    <StatCard label="Saved"   value={formatChf(sums.saved)} emphasis={sums.saved >= 0 ? "positive" : "negative"} />
  </div>
);
```

Remove the unused `useBudgetsForMonth` import and the `overCount` block.

- [ ] **Step 2: Update / write the render-smoke test**

Verify or create `frontend/src/components/dashboard/KpiRow.test.tsx`. Ensure it asserts the 4 cards: Income, Expense, Net, Saved.

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { KpiRow } from "./KpiRow";

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{node}</QueryClientProvider>;
}

describe("KpiRow", () => {
  it("renders Income, Expense, Net, Saved", async () => {
    render(wrap(<KpiRow month="2026-05" />));
    expect(await screen.findByText("Income")).toBeInTheDocument();
    expect(screen.getByText("Expense")).toBeInTheDocument();
    expect(screen.getByText("Net")).toBeInTheDocument();
    expect(screen.getByText("Saved")).toBeInTheDocument();
    expect(screen.queryByText(/Over budget/i)).toBeNull();
  });
});
```

- [ ] **Step 3: Run tests**

Run: `npm test -- KpiRow`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dashboard/KpiRow.tsx frontend/src/components/dashboard/KpiRow.test.tsx
git commit -m "feat(frontend): KpiRow drops Over-budget, adds Saved"
```

---

## Task 9: SavingsGoalCard component

**Files:**
- Create: `frontend/src/components/dashboard/SavingsGoalCard.tsx`
- Create: `frontend/src/components/dashboard/SavingsGoalCard.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SavingsGoalCard } from "./SavingsGoalCard";

describe("SavingsGoalCard", () => {
  it("shows saved / target, percent, and days-left", () => {
    render(
      <SavingsGoalCard
        name="Vacation 2027"
        saved={2400}
        target={3000}
        targetDate="2027-06-30"
        today={new Date("2026-11-27")}
      />,
    );
    expect(screen.getByText("Vacation 2027")).toBeInTheDocument();
    expect(screen.getByText(/2.+400.+\/ 3.+000/)).toBeInTheDocument();
    expect(screen.getByText(/80%/)).toBeInTheDocument();
    expect(screen.getByText(/215 days left/)).toBeInTheDocument();
  });

  it("omits days-left when targetDate is null", () => {
    render(
      <SavingsGoalCard
        name="Pillar 3a"
        saved={6300}
        target={7056}
        targetDate={null}
        today={new Date("2026-05-13")}
      />,
    );
    expect(screen.queryByText(/days left/)).toBeNull();
    expect(screen.getByText(/no deadline/i)).toBeInTheDocument();
  });

  it("renders a goal without target gracefully", () => {
    render(
      <SavingsGoalCard
        name="Emergency"
        saved={1200}
        target={null}
        targetDate={null}
        today={new Date("2026-05-13")}
      />,
    );
    expect(screen.getByText("Emergency")).toBeInTheDocument();
    expect(screen.getByText(/saved/i)).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- SavingsGoalCard`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `frontend/src/components/dashboard/SavingsGoalCard.tsx`:

```tsx
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { formatChf } from "@/lib/currency";

interface Props {
  name: string;
  saved: number;
  target: number | null;
  targetDate: string | null;  // ISO YYYY-MM-DD
  today?: Date;  // injectable for tests
}

function daysBetween(from: Date, toIso: string): number {
  const to = new Date(toIso + "T00:00:00");
  return Math.max(0, Math.round((to.getTime() - from.getTime()) / 86_400_000));
}

export function SavingsGoalCard({ name, saved, target, targetDate, today }: Props) {
  const now = today ?? new Date();
  const pct = target && target > 0 ? Math.min(100, Math.max(0, (saved / target) * 100)) : null;
  const days = targetDate ? daysBetween(now, targetDate) : null;
  const tone =
    pct === null ? "text-muted-foreground" :
    pct >= 100 ? "text-emerald-600 dark:text-emerald-500" :
    pct >= 80 ? "text-amber-600 dark:text-amber-400" : "";

  return (
    <Card>
      <CardContent className="py-4 space-y-2">
        <div className="font-medium">{name}</div>
        {target !== null ? (
          <>
            <div className="flex items-baseline gap-2">
              <span className="text-lg font-semibold tabular-nums">
                {formatChf(saved)}
              </span>
              <span className="text-muted-foreground text-sm">
                / {formatChf(target)}
              </span>
              <span className={`ml-auto text-sm font-medium ${tone}`}>
                {pct?.toFixed(0)}%
              </span>
            </div>
            <Progress value={pct ?? 0} />
            <div className="text-xs text-muted-foreground">
              {targetDate ? `${days} days left` : "no deadline"}
            </div>
          </>
        ) : (
          <div className="text-sm">
            <span className="tabular-nums">{formatChf(saved)}</span>{" "}
            <span className="text-muted-foreground">saved</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Ensure shadcn Progress component exists**

If `frontend/src/components/ui/progress.tsx` doesn't exist: `cd frontend; npx shadcn@latest add progress`.

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test -- SavingsGoalCard`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/dashboard/SavingsGoalCard.tsx frontend/src/components/dashboard/SavingsGoalCard.test.tsx frontend/src/components/ui/progress.tsx
git commit -m "feat(frontend): SavingsGoalCard with progress + days-left"
```

---

## Task 10: SavingsGoalsRow + Dashboard wiring

**Files:**
- Create: `frontend/src/components/dashboard/SavingsGoalsRow.tsx`
- Create: `frontend/src/components/dashboard/SavingsGoalsRow.test.tsx`
- Modify: `frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SavingsGoalsRow } from "./SavingsGoalsRow";

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{node}</QueryClientProvider>;
}

describe("SavingsGoalsRow", () => {
  it("renders one card per savings category with a target", async () => {
    render(wrap(<SavingsGoalsRow month="2026-05" />));
    // From the msw seed in handlers.ts, expect Vacation 2027 to render.
    expect(await screen.findByText(/Vacation 2027/i)).toBeInTheDocument();
  });

  it("renders nothing when no savings categories exist", async () => {
    // We rely on a hook that returns empty; assert no card section title.
    // If msw seed always has savings, this test can be skipped, but include
    // the structure for documentation.
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- SavingsGoalsRow`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `frontend/src/components/dashboard/SavingsGoalsRow.tsx`:

```tsx
import { useMemo } from "react";
import { useCategories } from "@/hooks/queries/useCategories";
import { useTransactions } from "@/hooks/queries/useTransactions";
import { SavingsGoalCard } from "./SavingsGoalCard";
import { Skeleton } from "@/components/ui/skeleton";

interface Props { month: string }

export function SavingsGoalsRow({ month }: Props) {
  const { data: cats, isLoading: catsLoading } = useCategories();
  // For cumulative goal progress we sum ALL savings transactions for that
  // category, not just the current month. Fetch with no month filter.
  const { data: allTxs, isLoading: txsLoading } = useTransactions({});

  const cards = useMemo(() => {
    if (!cats || !allTxs) return [];
    const savings = cats.filter((c) => c.kind === "savings");
    const sumsByCat = new Map<number, number>();
    for (const t of allTxs) {
      sumsByCat.set(t.category_id, (sumsByCat.get(t.category_id) ?? 0) + Number(t.amount));
    }
    return savings.map((c) => ({
      id: c.id,
      name: c.name,
      saved: sumsByCat.get(c.id) ?? 0,
      target: c.target_amount === null ? null : Number(c.target_amount),
      targetDate: c.target_date,
    }));
  }, [cats, allTxs]);

  if (catsLoading || txsLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
      </div>
    );
  }

  if (cards.length === 0) return null;

  return (
    <section>
      <h3 className="text-lg font-medium mb-3">Savings goals</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cards.map((c) => (
          <SavingsGoalCard
            key={c.id}
            name={c.name}
            saved={c.saved}
            target={c.target}
            targetDate={c.targetDate}
          />
        ))}
      </div>
    </section>
  );
}
```

If `useTransactions({})` doesn't currently support an empty filter for "all transactions", extend the hook signature now: passing `{}` should fetch with no `month` query param. Inspect `useTransactions.ts` and adjust.

- [ ] **Step 4: Wire into DashboardPage**

Modify `frontend/src/pages/DashboardPage.tsx`:

```tsx
import { KpiRow } from "@/components/dashboard/KpiRow";
import { BudgetWidget } from "@/components/dashboard/BudgetWidget";  // arrives in Task 11
import { RecentTransactions } from "@/components/dashboard/RecentTransactions";
import { CategoryDonut } from "@/components/dashboard/CategoryDonut";
import { MonthlyTrendBar } from "@/components/dashboard/MonthlyTrendBar";
import { SavingsGoalsRow } from "@/components/dashboard/SavingsGoalsRow";
import { useUrlMonth } from "@/hooks/useUrlMonth";
import { monthLabel } from "@/lib/date";

export default function DashboardPage() {
  const { month } = useUrlMonth();
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">
        Dashboard — {monthLabel(month)}
      </h2>
      <KpiRow month={month} />
      <SavingsGoalsRow month={month} />
      <BudgetWidget month={month} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <CategoryDonut month={month} />
        <MonthlyTrendBar month={month} />
      </div>
      <RecentTransactions month={month} />
    </div>
  );
}
```

Note: `BudgetWidget` is created in Task 11. To unblock Task 10's commit, you can leave a temporary `import { OverBudgetAlerts as BudgetWidget } from "@/components/dashboard/OverBudgetAlerts";` aliased here and replace it in Task 11. Or split Task 10's DashboardPage edit into Task 11 — your call. Either works; just stay consistent.

- [ ] **Step 5: Run tests**

Run: `npm test -- SavingsGoalsRow DashboardPage`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/dashboard/SavingsGoalsRow.tsx frontend/src/components/dashboard/SavingsGoalsRow.test.tsx frontend/src/pages/DashboardPage.tsx
git commit -m "feat(frontend): savings goals row on dashboard"
```

---

# Section B — Budget widget

## Task 11: BudgetWidget component

**Files:**
- Create: `frontend/src/components/dashboard/BudgetWidget.tsx`
- Create: `frontend/src/components/dashboard/BudgetWidget.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BudgetWidget } from "./BudgetWidget";

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{node}</QueryClientProvider>;
}

describe("BudgetWidget", () => {
  it("renders an aggregate top line and per-category rows sorted by % desc", async () => {
    render(wrap(<BudgetWidget month="2026-05" />));
    // Aggregate line: 'Spent X / Y' with overall percentage.
    expect(await screen.findByText(/spent/i)).toBeInTheDocument();
    expect(screen.getByText(/%/)).toBeInTheDocument();

    // First listed row should be the over-budget category from msw default seed.
    const rows = screen.getAllByRole("listitem");
    expect(rows.length).toBeGreaterThan(0);
    // First row's percent text > 100% (default seed includes an over-budget row).
    expect(within(rows[0]).getByText(/1\d\d%/)).toBeInTheDocument();
  });

  it("renders nothing when no budgets are set", async () => {
    // Empty-budgets case: assert a graceful empty-state message exists.
    // (Update msw handler in this test to return [].)
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- BudgetWidget`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `frontend/src/components/dashboard/BudgetWidget.tsx`:

```tsx
import { useMemo } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useBudgetsForMonth } from "@/hooks/queries/useBudgets";
import { formatChf } from "@/lib/currency";
import { monthLabel } from "@/lib/date";
import { cn } from "@/lib/utils";

interface Props { month: string }

function toneFor(pct: number): string {
  if (pct >= 100) return "text-destructive";
  if (pct >= 80) return "text-amber-600 dark:text-amber-400";
  return "text-emerald-600 dark:text-emerald-500";
}

function progressColor(pct: number): string {
  if (pct >= 100) return "bg-destructive";
  if (pct >= 80) return "bg-amber-500";
  return "bg-emerald-500";
}

export function BudgetWidget({ month }: Props) {
  const { data, isLoading } = useBudgetsForMonth(month);

  const rows = useMemo(() => {
    return (data ?? [])
      .map((b) => {
        const spent = Number(b.spent);
        const limit = Number(b.monthly_limit);
        const pct = limit > 0 ? (spent / limit) * 100 : 0;
        return { ...b, spent, limit, pct };
      })
      .sort((a, b) => b.pct - a.pct);
  }, [data]);

  const totals = rows.reduce(
    (acc, r) => {
      acc.spent += r.spent;
      acc.limit += r.limit;
      return acc;
    },
    { spent: 0, limit: 0 },
  );
  const totalPct = totals.limit > 0 ? (totals.spent / totals.limit) * 100 : 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle>Budgets · {monthLabel(month)}</CardTitle>
        <Link
          to="/budgets"
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          edit on /budgets
        </Link>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <Skeleton className="h-16 w-full" />
        ) : rows.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">
            No budgets set for this month. Set one on /budgets.
          </p>
        ) : (
          <>
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-lg font-semibold tabular-nums">
                  {formatChf(totals.spent)}
                </span>
                <span className="text-muted-foreground text-sm">
                  / {formatChf(totals.limit)}
                </span>
                <span className={cn("ml-auto text-sm font-medium", toneFor(totalPct))}>
                  {totalPct.toFixed(0)}%
                </span>
              </div>
              <Progress value={Math.min(100, totalPct)} className={progressColor(totalPct)} />
              <div className="text-xs text-muted-foreground">
                {formatChf(Math.max(0, totals.limit - totals.spent))} remaining
              </div>
            </div>

            <ul className="divide-y -mx-2">
              {rows.map((r) => (
                <li key={r.category_id} className="flex items-center gap-3 py-2 px-2">
                  <div className="w-32 truncate font-medium">{r.category_name}</div>
                  <div className="flex-1">
                    <Progress value={Math.min(100, r.pct)} className={progressColor(r.pct)} />
                  </div>
                  <div className="w-32 text-right tabular-nums text-sm">
                    {formatChf(r.spent)}
                    <span className="text-muted-foreground"> / {formatChf(r.limit)}</span>
                  </div>
                  <div className={cn("w-12 text-right text-sm font-medium", toneFor(r.pct))}>
                    {r.pct.toFixed(0)}%
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- BudgetWidget`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dashboard/BudgetWidget.tsx frontend/src/components/dashboard/BudgetWidget.test.tsx
git commit -m "feat(frontend): BudgetWidget with per-category progress + aggregate"
```

---

## Task 12: Wire BudgetWidget into Dashboard, retire OverBudgetAlerts

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx` (final form)
- Delete: `frontend/src/components/dashboard/OverBudgetAlerts.tsx`
- Delete: `frontend/src/components/dashboard/OverBudgetAlerts.test.tsx` (if present)

- [ ] **Step 1: Replace OverBudgetAlerts reference with BudgetWidget**

`DashboardPage.tsx` should now have:

```tsx
import { BudgetWidget } from "@/components/dashboard/BudgetWidget";
```

and use `<BudgetWidget month={month} />` in the layout shown in Task 10.

- [ ] **Step 2: Delete the old component file and its test (if present)**

```bash
git rm frontend/src/components/dashboard/OverBudgetAlerts.tsx
git rm -f frontend/src/components/dashboard/OverBudgetAlerts.test.tsx  # may not exist
```

- [ ] **Step 3: Run full frontend suite**

Run: `npm test`
Expected: all PASS, no unresolved imports.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat(frontend): retire OverBudgetAlerts, dashboard uses BudgetWidget"
```

---

# Section C — Icon + Title

## Task 13: Favicon SVG and page title

**Files:**
- Create: `frontend/public/favicon.svg`
- Modify: `frontend/index.html`

- [ ] **Step 1: Create the SVG favicon**

Create `frontend/public/favicon.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" aria-label="Financial Assistant">
  <circle cx="16" cy="16" r="15" fill="currentColor"/>
  <text
    x="16" y="22" text-anchor="middle"
    font-family="-apple-system, Segoe UI, Roboto, sans-serif"
    font-weight="700" font-size="16"
    fill="white"
  >Fr.</text>
</svg>
```

- [ ] **Step 2: Update index.html**

Replace `frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Financial Assistant</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 3: Smoke test the dev server**

Run: `cd frontend; npm run dev` (briefly), open `http://localhost:3000`, verify:
- Tab title reads "Financial Assistant"
- Favicon shows a colored circle with "Fr." in the address bar

Stop the dev server (Ctrl+C).

- [ ] **Step 4: Commit**

```bash
git add frontend/public/favicon.svg frontend/index.html
git commit -m "feat(frontend): page title 'Financial Assistant' + Fr. favicon"
```

---

# Section D — Sakura theme

## Task 14: useTheme supports `sakura`; index.css adds `.sakura` palette

**Files:**
- Modify: `frontend/src/hooks/useTheme.ts`
- Modify: `frontend/src/index.css`
- Modify or create: `frontend/src/hooks/useTheme.test.ts`

- [ ] **Step 1: Write a failing test**

Create or update `frontend/src/hooks/useTheme.test.ts`:

```ts
import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useTheme } from "./useTheme";

describe("useTheme (3-way)", () => {
  beforeEach(() => {
    document.documentElement.classList.remove("dark", "sakura");
    window.localStorage.clear();
  });

  it("setTheme('sakura') adds the .sakura class and removes .dark", () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setTheme("dark"));
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    act(() => result.current.setTheme("sakura"));
    expect(document.documentElement.classList.contains("sakura")).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("setTheme('light') removes both classes", () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setTheme("sakura"));
    act(() => result.current.setTheme("light"));
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(document.documentElement.classList.contains("sakura")).toBe(false);
  });

  it("persists sakura to localStorage", () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setTheme("sakura"));
    expect(window.localStorage.getItem("fa-theme")).toBe("sakura");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- useTheme`
Expected: FAIL — `setTheme("sakura")` is a type error, or class application doesn't include sakura.

- [ ] **Step 3: Update useTheme**

Replace `frontend/src/hooks/useTheme.ts`:

```ts
import { useEffect, useState } from "react";

type Theme = "light" | "dark" | "sakura";
const STORAGE_KEY = "fa-theme";

function readInitialTheme(): Theme {
  if (typeof window === "undefined") return "light";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark" || stored === "sakura") return stored;
  try {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  } catch {
    return "light";
  }
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(readInitialTheme);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("dark", "sakura");
    if (theme === "dark") root.classList.add("dark");
    else if (theme === "sakura") root.classList.add("sakura");
    window.localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  return {
    theme,
    setTheme,
  };
}
```

Note: the legacy `toggle()` method is removed because the toggle UX is now 3-segment (Task 15). If any other code calls `toggle()`, update it to call `setTheme("light"|"dark"|"sakura")` directly.

- [ ] **Step 4: Add .sakura block to index.css**

Append to `frontend/src/index.css` after the `.dark` block:

```css
.sakura {
  --background: 290 30% 8%;
  --foreground: 0 0% 96%;
  --card: 290 25% 12%;
  --card-foreground: 0 0% 96%;
  --popover: 290 25% 12%;
  --popover-foreground: 0 0% 96%;
  --primary: 340 65% 68%;
  --primary-foreground: 290 20% 10%;
  --secondary: 320 30% 22%;
  --secondary-foreground: 0 0% 96%;
  --muted: 290 20% 18%;
  --muted-foreground: 320 15% 65%;
  --accent: 320 30% 22%;
  --accent-foreground: 0 0% 96%;
  --destructive: 0 60% 55%;
  --destructive-foreground: 0 0% 98%;
  --border: 290 20% 22%;
  --input: 290 20% 22%;
  --ring: 340 50% 60%;
  --chart-1: 340 65% 68%;
  --chart-2: 280 50% 65%;
  --chart-3: 320 55% 70%;
  --chart-4:  10 65% 70%;
  --chart-5: 260 40% 55%;
}
```

- [ ] **Step 5: Run tests**

Run: `npm test -- useTheme`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/useTheme.ts frontend/src/hooks/useTheme.test.ts frontend/src/index.css
git commit -m "feat(frontend): sakura theme palette + 3-way useTheme hook"
```

---

## Task 15: 3-segment ThemeToggle

**Files:**
- Modify: `frontend/src/components/layout/ThemeToggle.tsx`
- Create: `frontend/src/components/layout/ThemeToggle.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ThemeToggle } from "./ThemeToggle";

describe("ThemeToggle (3-segment)", () => {
  beforeEach(() => {
    document.documentElement.classList.remove("dark", "sakura");
    window.localStorage.clear();
  });

  it("renders three buttons with aria-labels", () => {
    render(<ThemeToggle />);
    expect(screen.getByRole("button", { name: /sakura theme/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /light theme/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /dark theme/i })).toBeInTheDocument();
  });

  it("clicking sakura applies the .sakura class", () => {
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("button", { name: /sakura theme/i }));
    expect(document.documentElement.classList.contains("sakura")).toBe(true);
  });

  it("clicking dark applies .dark and removes .sakura", () => {
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("button", { name: /sakura theme/i }));
    fireEvent.click(screen.getByRole("button", { name: /dark theme/i }));
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(document.documentElement.classList.contains("sakura")).toBe(false);
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

Run: `npm test -- ThemeToggle`
Expected: FAIL — only one button rendered.

- [ ] **Step 3: Replace ThemeToggle**

```tsx
import { Moon, Sun, Flower2 } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { cn } from "@/lib/utils";

type ThemeName = "sakura" | "light" | "dark";
const OPTIONS: Array<{ key: ThemeName; label: string; Icon: React.ComponentType<{ className?: string }> }> = [
  { key: "sakura", label: "Sakura theme", Icon: Flower2 },
  { key: "light", label: "Light theme",  Icon: Sun },
  { key: "dark",  label: "Dark theme",   Icon: Moon },
];

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  return (
    <div className="inline-flex items-center rounded-md border bg-card p-0.5">
      {OPTIONS.map(({ key, label, Icon }) => (
        <button
          key={key}
          type="button"
          aria-label={label}
          aria-pressed={theme === key}
          onClick={() => setTheme(key)}
          className={cn(
            "inline-flex items-center justify-center h-7 w-7 rounded",
            theme === key
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-foreground",
          )}
        >
          <Icon className="h-4 w-4" />
        </button>
      ))}
    </div>
  );
}
```

(If `Flower2` isn't in your `lucide-react` version, use `Cherry` or any other flower-ish icon — verify the import resolves before running tests.)

- [ ] **Step 4: Run tests**

Run: `npm test -- ThemeToggle`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/ThemeToggle.tsx frontend/src/components/layout/ThemeToggle.test.tsx
git commit -m "feat(frontend): 3-segment sakura/light/dark theme toggle"
```

---

# Section E — CSV Import

## Task 16: ImportPreset model + schemas + service + router

**Files:**
- Create: `backend/app/models/import_preset.py`
- Create: `backend/app/schemas/import_preset.py`
- Create: `backend/app/services/import_preset_service.py`
- Create: `backend/app/routers/import_presets.py`
- Create: `backend/tests/test_import_preset_service.py`
- Create: `backend/tests/test_routes/test_import_presets.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/main.py` (include router)

- [ ] **Step 1: Write the failing service test**

`backend/tests/test_import_preset_service.py`:

```python
import pytest

from app.services import import_preset_service


def test_create_preset(db_session):
    p = import_preset_service.create_preset(
        db_session,
        user_id=1,
        name="UBS",
        config={"delimiter": ";", "decimal_sep": ".", "amount_format": "signed"},
    )
    assert p.id is not None
    assert p.name == "UBS"
    assert p.config["delimiter"] == ";"


def test_list_presets_returns_only_users_own(db_session):
    import_preset_service.create_preset(db_session, user_id=1, name="UBS",  config={})
    import_preset_service.create_preset(db_session, user_id=1, name="Raif", config={})
    import_preset_service.create_preset(db_session, user_id=2, name="X",    config={})
    names = sorted(p.name for p in import_preset_service.list_presets(db_session, user_id=1))
    assert names == ["Raif", "UBS"]


def test_create_preset_rejects_duplicate_name_for_same_user(db_session):
    import_preset_service.create_preset(db_session, user_id=1, name="UBS", config={})
    with pytest.raises(ValueError, match="already exists"):
        import_preset_service.create_preset(db_session, user_id=1, name="UBS", config={})


def test_update_preset_changes_config(db_session):
    p = import_preset_service.create_preset(db_session, user_id=1, name="UBS", config={"a": 1})
    updated = import_preset_service.update_preset(
        db_session, user_id=1, preset_id=p.id, name="UBS",  config={"a": 2}
    )
    assert updated.config == {"a": 2}


def test_delete_preset(db_session):
    p = import_preset_service.create_preset(db_session, user_id=1, name="UBS", config={})
    import_preset_service.delete_preset(db_session, user_id=1, preset_id=p.id)
    assert import_preset_service.list_presets(db_session, user_id=1) == []
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/test_import_preset_service.py -v`
Expected: FAIL — modules don't exist.

- [ ] **Step 3: Create the model**

`backend/app/models/import_preset.py`:

```python
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ImportPreset(Base):
    __tablename__ = "import_presets"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_preset_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

Register in `backend/app/models/__init__.py`:

```python
from app.models.import_preset import ImportPreset  # noqa: F401
```

- [ ] **Step 4: Create schemas**

`backend/app/schemas/import_preset.py`:

```python
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ImportPresetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    config: dict[str, Any] = Field(default_factory=dict)


class ImportPresetUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    config: dict[str, Any] = Field(default_factory=dict)


class ImportPresetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 5: Create the service**

`backend/app/services/import_preset_service.py`:

```python
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.import_preset import ImportPreset


def create_preset(
    db: Session, *, user_id: int, name: str, config: dict[str, Any]
) -> ImportPreset:
    existing = db.execute(
        select(ImportPreset).where(
            ImportPreset.user_id == user_id, ImportPreset.name == name
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError(f"Preset '{name}' already exists")

    p = ImportPreset(user_id=user_id, name=name, config=config)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def list_presets(db: Session, *, user_id: int) -> list[ImportPreset]:
    rows = db.execute(
        select(ImportPreset).where(ImportPreset.user_id == user_id).order_by(ImportPreset.name)
    ).scalars().all()
    return list(rows)


def get_preset(db: Session, *, user_id: int, preset_id: int) -> ImportPreset | None:
    return db.execute(
        select(ImportPreset).where(
            ImportPreset.id == preset_id, ImportPreset.user_id == user_id
        )
    ).scalar_one_or_none()


def update_preset(
    db: Session,
    *,
    user_id: int,
    preset_id: int,
    name: str,
    config: dict[str, Any],
) -> ImportPreset:
    p = get_preset(db, user_id=user_id, preset_id=preset_id)
    if p is None:
        raise LookupError(f"Preset {preset_id} not found")
    p.name = name
    p.config = config
    db.commit()
    db.refresh(p)
    return p


def delete_preset(db: Session, *, user_id: int, preset_id: int) -> None:
    p = get_preset(db, user_id=user_id, preset_id=preset_id)
    if p is None:
        raise LookupError(f"Preset {preset_id} not found")
    db.delete(p)
    db.commit()
```

- [ ] **Step 6: Create the router**

`backend/app/routers/import_presets.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.import_preset import (
    ImportPresetCreate,
    ImportPresetRead,
    ImportPresetUpdate,
)
from app.services import import_preset_service

router = APIRouter(prefix="/api/import-presets", tags=["import-presets"])


@router.get("", response_model=list[ImportPresetRead])
def list_presets(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return import_preset_service.list_presets(db, user_id=user_id)


@router.post("", response_model=ImportPresetRead, status_code=status.HTTP_201_CREATED)
def create_preset(
    payload: ImportPresetCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return import_preset_service.create_preset(
            db, user_id=user_id, name=payload.name, config=payload.config
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{preset_id}", response_model=ImportPresetRead)
def update_preset(
    preset_id: int,
    payload: ImportPresetUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return import_preset_service.update_preset(
            db, user_id=user_id, preset_id=preset_id, name=payload.name, config=payload.config
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preset(
    preset_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        import_preset_service.delete_preset(db, user_id=user_id, preset_id=preset_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
```

Include in `backend/app/main.py`:

```python
from app.routers import budgets, categories, csv_import, export, health, import_presets, transactions
# ...
app.include_router(import_presets.router)
# (csv_import added in Task 18)
```

- [ ] **Step 7: Write route smoke tests**

`backend/tests/test_routes/test_import_presets.py`:

```python
def test_create_and_list_preset(client):
    r = client.post("/api/import-presets", json={"name": "UBS", "config": {"delimiter": ";"}})
    assert r.status_code == 201
    pid = r.json()["id"]
    r = client.get("/api/import-presets")
    names = [p["name"] for p in r.json()]
    assert "UBS" in names
    assert any(p["id"] == pid for p in r.json())


def test_update_preset(client):
    pid = client.post("/api/import-presets", json={"name": "UBS", "config": {}}).json()["id"]
    r = client.put(f"/api/import-presets/{pid}", json={"name": "UBS-2", "config": {"a": 1}})
    assert r.status_code == 200
    assert r.json()["name"] == "UBS-2"
    assert r.json()["config"] == {"a": 1}


def test_delete_preset(client):
    pid = client.post("/api/import-presets", json={"name": "UBS", "config": {}}).json()["id"]
    r = client.delete(f"/api/import-presets/{pid}")
    assert r.status_code == 204
    assert client.get("/api/import-presets").json() == []
```

- [ ] **Step 8: Run all backend tests**

Run: `pytest -v`
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/import_preset.py backend/app/schemas/import_preset.py backend/app/services/import_preset_service.py backend/app/routers/import_presets.py backend/app/models/__init__.py backend/app/main.py backend/tests/test_import_preset_service.py backend/tests/test_routes/test_import_presets.py
git commit -m "feat(backend): import_presets CRUD"
```

---

## Task 17: CSV parser service

**Files:**
- Create: `backend/app/services/csv_import_service.py`
- Create: `backend/app/schemas/csv_import.py`
- Create: `backend/tests/test_csv_import_service.py`

- [ ] **Step 1: Define the config + result shape (schemas)**

`backend/app/schemas/csv_import.py`:

```python
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AmountFormat = Literal["signed", "debit_credit"]
SignConvention = Literal["negative_is_expense", "negative_is_income"]


class CsvColumnMapping(BaseModel):
    date: int                 # 0-based column index
    description: int
    amount: int | None = None        # signed mode
    debit: int | None = None         # debit_credit mode
    credit: int | None = None        # debit_credit mode


class CsvImportConfig(BaseModel):
    delimiter: str = ";"
    decimal_sep: str = "."
    thousands_sep: str = ""
    date_format: str = "%Y-%m-%d"    # strftime format
    skip_header_rows: int = 0
    has_header: bool = False
    amount_format: AmountFormat = "signed"
    sign_convention: SignConvention = "negative_is_expense"
    cols: CsvColumnMapping


class ParsedRow(BaseModel):
    row_index: int            # 0-based after skip_header_rows
    date: date | None = None
    description: str = ""
    amount: Decimal | None = None
    kind_hint: Literal["income", "expense"] | None = None  # derived from sign
    errors: list[str] = Field(default_factory=list)


class CsvPreviewRequest(BaseModel):
    file_content: str
    config: CsvImportConfig


class CsvPreviewResponse(BaseModel):
    rows: list[ParsedRow]


class ImportCommitRowSelection(BaseModel):
    row_index: int
    category_id: int
    is_recurring: bool = False


class ImportCommitRequest(BaseModel):
    file_content: str
    config: CsvImportConfig
    selections: list[ImportCommitRowSelection]


class ImportCommitResponse(BaseModel):
    imported: int
    skipped: int
```

- [ ] **Step 2: Write the failing parser tests**

`backend/tests/test_csv_import_service.py`:

```python
from datetime import date
from decimal import Decimal

from app.schemas.csv_import import CsvColumnMapping, CsvImportConfig
from app.services.csv_import_service import parse_csv


def _cfg(**over):
    base = dict(
        delimiter=";",
        decimal_sep=".",
        thousands_sep="",
        date_format="%Y-%m-%d",
        skip_header_rows=0,
        has_header=False,
        amount_format="signed",
        sign_convention="negative_is_expense",
        cols=CsvColumnMapping(date=0, description=1, amount=2),
    )
    base.update(over)
    return CsvImportConfig(**base)


def test_parse_minimal_signed_csv():
    text = "2026-05-13;COOP Zürich;-45.30\n2026-05-13;Salary;+5200\n"
    rows = parse_csv(text, _cfg())
    assert len(rows) == 2
    assert rows[0].date == date(2026, 5, 13)
    assert rows[0].description == "COOP Zürich"
    assert rows[0].amount == Decimal("-45.30")
    assert rows[0].kind_hint == "expense"
    assert rows[1].amount == Decimal("5200")
    assert rows[1].kind_hint == "income"
    assert all(r.errors == [] for r in rows)


def test_parse_swiss_decimals_and_thousands():
    text = "2026-05-13;Salary;5'200,50\n"
    cfg = _cfg(decimal_sep=",", thousands_sep="'")
    rows = parse_csv(text, cfg)
    assert rows[0].amount == Decimal("5200.50")


def test_parse_skips_header_rows():
    text = "preamble1\npreamble2\nDate;Desc;Amount\n2026-05-13;X;-10\n"
    cfg = _cfg(skip_header_rows=2, has_header=True)
    rows = parse_csv(text, cfg)
    assert len(rows) == 1
    assert rows[0].description == "X"


def test_parse_debit_credit_layout():
    text = "2026-05-13;COOP;45.30;\n2026-05-13;Salary;;5200\n"
    cfg = _cfg(
        amount_format="debit_credit",
        cols=CsvColumnMapping(date=0, description=1, debit=2, credit=3),
    )
    rows = parse_csv(text, cfg)
    assert rows[0].amount == Decimal("-45.30")
    assert rows[0].kind_hint == "expense"
    assert rows[1].amount == Decimal("5200")
    assert rows[1].kind_hint == "income"


def test_parse_row_with_bad_date_flags_error_but_does_not_raise():
    text = "not-a-date;X;10\n"
    rows = parse_csv(text, _cfg())
    assert rows[0].errors
    assert "date" in rows[0].errors[0].lower()


def test_parse_european_date_format():
    text = "13.05.2026;X;10\n"
    cfg = _cfg(date_format="%d.%m.%Y")
    rows = parse_csv(text, cfg)
    assert rows[0].date == date(2026, 5, 13)
    assert rows[0].errors == []
```

- [ ] **Step 3: Run tests to verify failure**

Run: `pytest tests/test_csv_import_service.py -v`
Expected: FAIL — module not found.

- [ ] **Step 4: Implement parser**

`backend/app/services/csv_import_service.py`:

```python
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import StringIO

from app.schemas.csv_import import CsvImportConfig, ParsedRow


def _normalize_number(raw: str, decimal_sep: str, thousands_sep: str) -> Decimal:
    s = raw.strip()
    if not s:
        raise InvalidOperation("empty")
    if thousands_sep:
        s = s.replace(thousands_sep, "")
    if decimal_sep != ".":
        s = s.replace(decimal_sep, ".")
    s = s.replace("+", "")
    return Decimal(s)


def parse_csv(text: str, config: CsvImportConfig) -> list[ParsedRow]:
    reader = csv.reader(StringIO(text), delimiter=config.delimiter)
    all_rows = list(reader)

    start = config.skip_header_rows + (1 if config.has_header else 0)
    data = all_rows[start:]

    out: list[ParsedRow] = []
    cols = config.cols

    for idx, raw in enumerate(data):
        row = ParsedRow(row_index=idx)
        try:
            row.date = datetime.strptime(raw[cols.date].strip(), config.date_format).date()
        except (ValueError, IndexError) as exc:
            row.errors.append(f"bad date: {exc}")

        try:
            row.description = raw[cols.description].strip()
        except IndexError:
            row.errors.append("missing description column")

        if config.amount_format == "signed":
            if cols.amount is None:
                row.errors.append("config: amount column not set")
            else:
                try:
                    n = _normalize_number(raw[cols.amount], config.decimal_sep, config.thousands_sep)
                    row.amount = n
                except (InvalidOperation, IndexError) as exc:
                    row.errors.append(f"bad amount: {exc}")
        else:
            if cols.debit is None or cols.credit is None:
                row.errors.append("config: debit/credit columns not set")
            else:
                try:
                    d_raw = raw[cols.debit].strip() if cols.debit < len(raw) else ""
                    c_raw = raw[cols.credit].strip() if cols.credit < len(raw) else ""
                    if d_raw and c_raw:
                        row.errors.append("both debit and credit populated")
                    elif d_raw:
                        n = _normalize_number(d_raw, config.decimal_sep, config.thousands_sep)
                        row.amount = -abs(n)
                    elif c_raw:
                        n = _normalize_number(c_raw, config.decimal_sep, config.thousands_sep)
                        row.amount = abs(n)
                    else:
                        row.errors.append("debit and credit both empty")
                except (InvalidOperation, IndexError) as exc:
                    row.errors.append(f"bad amount: {exc}")

        if row.amount is not None:
            if config.sign_convention == "negative_is_expense":
                row.kind_hint = "expense" if row.amount < 0 else "income"
            else:
                row.kind_hint = "income" if row.amount < 0 else "expense"

        out.append(row)

    return out
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_csv_import_service.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/csv_import_service.py backend/app/schemas/csv_import.py backend/tests/test_csv_import_service.py
git commit -m "feat(backend): CSV parser service with signed + debit/credit layouts"
```

---

## Task 18: Preview + commit endpoints with dupe detection

**Files:**
- Create: `backend/app/routers/csv_import.py`
- Create: `backend/tests/test_routes/test_csv_import.py`
- Modify: `backend/app/main.py` (include csv_import router)

- [ ] **Step 1: Write the failing route tests**

`backend/tests/test_routes/test_csv_import.py`:

```python
def _seed_category(client, name="Imported", kind="expense"):
    return client.post("/api/categories", json={"name": name, "kind": kind}).json()


def test_preview_returns_parsed_rows(client):
    payload = {
        "file_content": "2026-05-13;COOP;-45.30\n2026-05-13;Salary;5200\n",
        "config": {
            "delimiter": ";", "decimal_sep": ".", "thousands_sep": "",
            "date_format": "%Y-%m-%d", "skip_header_rows": 0, "has_header": False,
            "amount_format": "signed", "sign_convention": "negative_is_expense",
            "cols": {"date": 0, "description": 1, "amount": 2},
        },
    }
    r = client.post("/api/import/preview", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert len(body["rows"]) == 2
    assert body["rows"][0]["kind_hint"] == "expense"
    assert body["rows"][1]["kind_hint"] == "income"


def test_preview_flags_dupes(client):
    cat = _seed_category(client)
    # Seed a transaction matching what will appear in the CSV.
    client.post("/api/transactions", json={
        "amount": "45.30", "date": "2026-05-13", "category_id": cat["id"],
        "description": "COOP",
    })
    payload = {
        "file_content": "2026-05-13;COOP;-45.30\n2026-05-13;Salary;5200\n",
        "config": {
            "delimiter": ";", "decimal_sep": ".", "thousands_sep": "",
            "date_format": "%Y-%m-%d", "skip_header_rows": 0, "has_header": False,
            "amount_format": "signed", "sign_convention": "negative_is_expense",
            "cols": {"date": 0, "description": 1, "amount": 2},
        },
    }
    r = client.post("/api/import/preview", json=payload)
    body = r.json()
    assert body["rows"][0]["is_duplicate"] is True
    assert body["rows"][1]["is_duplicate"] is False


def test_commit_creates_only_selected_rows(client):
    cat = _seed_category(client)
    payload = {
        "file_content": "2026-05-13;COOP;-45.30\n2026-05-13;Salary;5200\n",
        "config": {
            "delimiter": ";", "decimal_sep": ".", "thousands_sep": "",
            "date_format": "%Y-%m-%d", "skip_header_rows": 0, "has_header": False,
            "amount_format": "signed", "sign_convention": "negative_is_expense",
            "cols": {"date": 0, "description": 1, "amount": 2},
        },
        "selections": [
            {"row_index": 0, "category_id": cat["id"], "is_recurring": False},
            # row_index 1 omitted -> skipped
        ],
    }
    r = client.post("/api/import/commit", json=payload)
    assert r.status_code == 200
    assert r.json() == {"imported": 1, "skipped": 1}

    txs = client.get("/api/transactions?month=2026-05").json()
    assert len(txs) == 1
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_routes/test_csv_import.py -v`
Expected: FAIL — endpoints missing.

- [ ] **Step 3: Extend `ParsedRow` to carry a `is_duplicate` flag**

Update `backend/app/schemas/csv_import.py`:

```python
class ParsedRow(BaseModel):
    row_index: int
    date: date | None = None
    description: str = ""
    amount: Decimal | None = None
    kind_hint: Literal["income", "expense"] | None = None
    is_duplicate: bool = False
    errors: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Implement the router with dupe detection**

`backend/app/routers/csv_import.py`:

```python
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.transaction import Transaction
from app.schemas.csv_import import (
    CsvPreviewRequest,
    CsvPreviewResponse,
    ImportCommitRequest,
    ImportCommitResponse,
    ParsedRow,
)
from app.services import csv_import_service, transaction_service

router = APIRouter(prefix="/api/import", tags=["import"])


def _mark_duplicates(db: Session, user_id: int, rows: list[ParsedRow]) -> None:
    keys = {(r.date, abs(r.amount), r.description) for r in rows if r.date and r.amount is not None}
    if not keys:
        return
    existing = db.execute(
        select(Transaction.date, Transaction.amount, Transaction.description).where(
            Transaction.user_id == user_id
        )
    ).all()
    existing_keys = {(d, abs(Decimal(a)), desc) for d, a, desc in existing}
    for r in rows:
        if r.date and r.amount is not None and (r.date, abs(r.amount), r.description) in existing_keys:
            r.is_duplicate = True


@router.post("/preview", response_model=CsvPreviewResponse)
def preview(
    payload: CsvPreviewRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    rows = csv_import_service.parse_csv(payload.file_content, payload.config)
    _mark_duplicates(db, user_id, rows)
    return CsvPreviewResponse(rows=rows)


@router.post("/commit", response_model=ImportCommitResponse)
def commit(
    payload: ImportCommitRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    rows = csv_import_service.parse_csv(payload.file_content, payload.config)
    by_index = {r.row_index: r for r in rows}
    imported = 0
    skipped = 0

    for sel in payload.selections:
        r = by_index.get(sel.row_index)
        if r is None or r.errors or r.amount is None or r.date is None:
            skipped += 1
            continue
        try:
            transaction_service.create_transaction(
                db,
                user_id=user_id,
                amount=r.amount,
                date=r.date,
                category_id=sel.category_id,
                description=r.description,
                is_recurring=sel.is_recurring,
            )
            imported += 1
        except (ValueError, LookupError) as exc:
            skipped += 1

    skipped += len(rows) - len(payload.selections)
    return ImportCommitResponse(imported=imported, skipped=skipped)
```

Wire it in `backend/app/main.py`:

```python
from app.routers import budgets, categories, csv_import, export, health, import_presets, transactions
# ...
app.include_router(csv_import.router)
```

- [ ] **Step 5: Run tests**

Run: `pytest -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/csv_import.py backend/app/schemas/csv_import.py backend/app/main.py backend/tests/test_routes/test_csv_import.py
git commit -m "feat(backend): /api/import preview + commit with dupe detection"
```

---

## Task 19: Frontend import API client + types + sidebar route

**Files:**
- Modify: `frontend/src/api/types.ts` (add Import types)
- Create: `frontend/src/api/import-presets.ts`
- Create: `frontend/src/api/csv-import.ts`
- Create: `frontend/src/hooks/queries/useImportPresets.ts`
- Modify: `frontend/src/routes.tsx`
- Modify: `frontend/src/components/layout/Sidebar.tsx`
- Create: `frontend/src/pages/ImportPage.tsx` (stub for now)

- [ ] **Step 1: Add types**

Append to `frontend/src/api/types.ts`:

```ts
export type AmountFormat = "signed" | "debit_credit";
export type SignConvention = "negative_is_expense" | "negative_is_income";

export interface CsvColumnMapping {
  date: number;
  description: number;
  amount?: number | null;
  debit?: number | null;
  credit?: number | null;
}

export interface CsvImportConfig {
  delimiter: string;
  decimal_sep: string;
  thousands_sep: string;
  date_format: string;
  skip_header_rows: number;
  has_header: boolean;
  amount_format: AmountFormat;
  sign_convention: SignConvention;
  cols: CsvColumnMapping;
}

export interface ParsedRow {
  row_index: number;
  date: string | null;
  description: string;
  amount: string | null;
  kind_hint: "income" | "expense" | null;
  is_duplicate: boolean;
  errors: string[];
}

export interface ImportPreset {
  id: number;
  name: string;
  config: CsvImportConfig;
  created_at: string;
  updated_at: string;
}

export interface ImportPresetCreatePayload {
  name: string;
  config: CsvImportConfig;
}

export interface ImportCommitRowSelection {
  row_index: number;
  category_id: number;
  is_recurring: boolean;
}

export interface ImportCommitResponse {
  imported: number;
  skipped: number;
}
```

- [ ] **Step 2: Create import-presets API client**

`frontend/src/api/import-presets.ts`:

```ts
import { apiFetch } from "./client";
import type { ImportPreset, ImportPresetCreatePayload } from "./types";

export function listImportPresets(): Promise<ImportPreset[]> {
  return apiFetch<ImportPreset[]>("/api/import-presets");
}

export function createImportPreset(p: ImportPresetCreatePayload): Promise<ImportPreset> {
  return apiFetch<ImportPreset>("/api/import-presets", {
    method: "POST",
    body: JSON.stringify(p),
  });
}

export function updateImportPreset(
  id: number,
  p: ImportPresetCreatePayload,
): Promise<ImportPreset> {
  return apiFetch<ImportPreset>(`/api/import-presets/${id}`, {
    method: "PUT",
    body: JSON.stringify(p),
  });
}

export function deleteImportPreset(id: number): Promise<void> {
  return apiFetch<void>(`/api/import-presets/${id}`, { method: "DELETE" });
}
```

- [ ] **Step 3: Create csv-import API client**

`frontend/src/api/csv-import.ts`:

```ts
import { apiFetch } from "./client";
import type {
  CsvImportConfig, ImportCommitResponse, ImportCommitRowSelection, ParsedRow,
} from "./types";

export function previewCsv(
  fileContent: string, config: CsvImportConfig,
): Promise<{ rows: ParsedRow[] }> {
  return apiFetch<{ rows: ParsedRow[] }>("/api/import/preview", {
    method: "POST",
    body: JSON.stringify({ file_content: fileContent, config }),
  });
}

export function commitImport(
  fileContent: string,
  config: CsvImportConfig,
  selections: ImportCommitRowSelection[],
): Promise<ImportCommitResponse> {
  return apiFetch<ImportCommitResponse>("/api/import/commit", {
    method: "POST",
    body: JSON.stringify({ file_content: fileContent, config, selections }),
  });
}
```

- [ ] **Step 4: Query hook**

`frontend/src/hooks/queries/useImportPresets.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createImportPreset, deleteImportPreset, listImportPresets, updateImportPreset,
} from "@/api/import-presets";
import type { ImportPresetCreatePayload } from "@/api/types";

const KEY = ["import-presets"] as const;

export function useImportPresets() {
  return useQuery({ queryKey: KEY, queryFn: listImportPresets });
}

export function useCreateImportPreset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: ImportPresetCreatePayload) => createImportPreset(p),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateImportPreset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ImportPresetCreatePayload }) =>
      updateImportPreset(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteImportPreset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteImportPreset(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
```

- [ ] **Step 5: ImportPage stub**

`frontend/src/pages/ImportPage.tsx`:

```tsx
export default function ImportPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Import</h2>
      <p className="text-muted-foreground">Upload + configure flow — built in Tasks 20/21.</p>
    </div>
  );
}
```

- [ ] **Step 6: Add route + sidebar link**

`frontend/src/routes.tsx`:

```tsx
import ImportPage from "@/pages/ImportPage";
// ...
{ path: "import", element: <ImportPage /> },
```

`frontend/src/components/layout/Sidebar.tsx`:

```tsx
import {
  LayoutDashboard, Receipt, Tag, Wallet, Download, Upload,
} from "lucide-react";

const links = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/transactions", label: "Transactions", icon: Receipt },
  { to: "/categories", label: "Categories", icon: Tag },
  { to: "/budgets", label: "Budgets", icon: Wallet },
  { to: "/import", label: "Import", icon: Upload },
  { to: "/export", label: "Export", icon: Download },
];
```

- [ ] **Step 7: Run frontend tests**

Run: `npm test`
Expected: all PASS, no broken imports.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/import-presets.ts frontend/src/api/csv-import.ts frontend/src/hooks/queries/useImportPresets.ts frontend/src/pages/ImportPage.tsx frontend/src/routes.tsx frontend/src/components/layout/Sidebar.tsx
git commit -m "feat(frontend): import types, API clients, sidebar nav, page stub"
```

---

## Task 20: ImportConfigPanel + CsvHelpPanel

**Files:**
- Create: `frontend/src/components/imports/ImportConfigPanel.tsx`
- Create: `frontend/src/components/imports/CsvHelpPanel.tsx`
- Create: tests for each

- [ ] **Step 1: Write a smoke test for the config panel**

`frontend/src/components/imports/ImportConfigPanel.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ImportConfigPanel } from "./ImportConfigPanel";
import type { CsvImportConfig } from "@/api/types";

const defaultConfig: CsvImportConfig = {
  delimiter: ";", decimal_sep: ".", thousands_sep: "",
  date_format: "%Y-%m-%d", skip_header_rows: 0, has_header: false,
  amount_format: "signed", sign_convention: "negative_is_expense",
  cols: { date: 0, description: 1, amount: 2 },
};

describe("ImportConfigPanel", () => {
  it("calls onChange when delimiter changes", () => {
    const onChange = vi.fn();
    render(<ImportConfigPanel config={defaultConfig} onChange={onChange} />);
    fireEvent.click(screen.getByLabelText(/delimiter/i));
    fireEvent.click(screen.getByRole("option", { name: "," }));
    expect(onChange).toHaveBeenCalled();
    const next = onChange.mock.calls.at(-1)![0];
    expect(next.delimiter).toBe(",");
  });
});
```

- [ ] **Step 2: Implement ImportConfigPanel**

`frontend/src/components/imports/ImportConfigPanel.tsx`:

```tsx
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import type { CsvImportConfig } from "@/api/types";

interface Props {
  config: CsvImportConfig;
  onChange: (next: CsvImportConfig) => void;
}

export function ImportConfigPanel({ config, onChange }: Props) {
  function set<K extends keyof CsvImportConfig>(k: K, v: CsvImportConfig[K]) {
    onChange({ ...config, [k]: v });
  }
  function setCol<K extends keyof CsvImportConfig["cols"]>(k: K, v: number | null) {
    onChange({ ...config, cols: { ...config.cols, [k]: v } });
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="cfg-delim">Delimiter</Label>
          <Select value={config.delimiter} onValueChange={(v) => set("delimiter", v)}>
            <SelectTrigger id="cfg-delim" aria-label="Delimiter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value=";">;</SelectItem>
              <SelectItem value=",">,</SelectItem>
              <SelectItem value="\t">tab</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="cfg-dec">Decimal separator</Label>
          <Select value={config.decimal_sep} onValueChange={(v) => set("decimal_sep", v)}>
            <SelectTrigger id="cfg-dec"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value=".">.</SelectItem>
              <SelectItem value=",">,</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="cfg-thou">Thousands separator</Label>
          <Select value={config.thousands_sep} onValueChange={(v) => set("thousands_sep", v)}>
            <SelectTrigger id="cfg-thou"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="">(none)</SelectItem>
              <SelectItem value="'">'</SelectItem>
              <SelectItem value=".">.</SelectItem>
              <SelectItem value=",">,</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="cfg-date">Date format (strftime)</Label>
          <Input
            id="cfg-date"
            value={config.date_format}
            onChange={(e) => set("date_format", e.target.value)}
            placeholder="%d.%m.%Y"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="cfg-skip">Skip header rows</Label>
          <Input
            id="cfg-skip"
            type="number" min={0}
            value={config.skip_header_rows}
            onChange={(e) => set("skip_header_rows", Number(e.target.value))}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="cfg-fmt">Amount format</Label>
          <Select
            value={config.amount_format}
            onValueChange={(v) => set("amount_format", v as CsvImportConfig["amount_format"])}
          >
            <SelectTrigger id="cfg-fmt"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="signed">Single signed Amount</SelectItem>
              <SelectItem value="debit_credit">Separate Debit / Credit</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <div className="font-medium">Column mapping (0-based)</div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          <ColumnInput label="Date col" value={config.cols.date} onChange={(n) => setCol("date", n)} />
          <ColumnInput label="Description col" value={config.cols.description} onChange={(n) => setCol("description", n)} />
          {config.amount_format === "signed" ? (
            <ColumnInput label="Amount col" value={config.cols.amount ?? 0} onChange={(n) => setCol("amount", n)} />
          ) : (
            <>
              <ColumnInput label="Debit col"  value={config.cols.debit  ?? 0} onChange={(n) => setCol("debit",  n)} />
              <ColumnInput label="Credit col" value={config.cols.credit ?? 0} onChange={(n) => setCol("credit", n)} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function ColumnInput({
  label, value, onChange,
}: { label: string; value: number; onChange: (n: number) => void }) {
  return (
    <div className="space-y-1">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Input type="number" min={0} value={value} onChange={(e) => onChange(Number(e.target.value))} />
    </div>
  );
}
```

- [ ] **Step 3: Implement CsvHelpPanel**

`frontend/src/components/imports/CsvHelpPanel.tsx`:

```tsx
import { ChevronDown } from "lucide-react";
import { useState } from "react";

export function CsvHelpPanel() {
  const [open, setOpen] = useState(false);
  return (
    <details className="border rounded-md p-3" onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary className="cursor-pointer flex items-center gap-2 font-medium select-none">
        <ChevronDown className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`} />
        What should my CSV look like?
      </summary>

      <div className="mt-3 space-y-4 text-sm">
        <div>
          <div className="font-medium mb-1">Layout A — single signed Amount</div>
          <table className="text-xs border w-full">
            <thead className="bg-muted">
              <tr><th className="text-left p-1">Date</th><th className="text-left p-1">Description</th><th className="text-left p-1">Amount</th></tr>
            </thead>
            <tbody>
              <tr><td className="p-1">03.05.26</td><td className="p-1">COOP Zürich</td><td className="p-1">-45.30 <span className="text-muted-foreground">← expense</span></td></tr>
              <tr><td className="p-1">03.05.26</td><td className="p-1">Salary May</td><td className="p-1">+5200 <span className="text-muted-foreground">← income</span></td></tr>
            </tbody>
          </table>
        </div>

        <div>
          <div className="font-medium mb-1">Layout B — separate Debit / Credit</div>
          <table className="text-xs border w-full">
            <thead className="bg-muted">
              <tr><th className="text-left p-1">Date</th><th className="text-left p-1">Description</th><th className="text-left p-1">Debit</th><th className="text-left p-1">Credit</th></tr>
            </thead>
            <tbody>
              <tr><td className="p-1">03.05.26</td><td className="p-1">COOP Zürich</td><td className="p-1">45.30</td><td className="p-1"></td></tr>
              <tr><td className="p-1">03.05.26</td><td className="p-1">Salary May</td><td className="p-1"></td><td className="p-1">5200</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </details>
  );
}
```

- [ ] **Step 4: Run tests**

Run: `npm test -- ImportConfigPanel`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/imports/ImportConfigPanel.tsx frontend/src/components/imports/ImportConfigPanel.test.tsx frontend/src/components/imports/CsvHelpPanel.tsx
git commit -m "feat(frontend): ImportConfigPanel + CsvHelpPanel"
```

---

## Task 21: ImportPreviewTable + ImportPage main flow

**Files:**
- Create: `frontend/src/components/imports/ImportPreviewTable.tsx`
- Modify: `frontend/src/pages/ImportPage.tsx`
- Create: tests

- [ ] **Step 1: Write a smoke test for ImportPreviewTable**

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ImportPreviewTable } from "./ImportPreviewTable";
import type { ParsedRow, Category } from "@/api/types";

const cats: Category[] = [
  { id: 1, name: "Imported", kind: "expense", target_amount: null, target_date: null, created_at: "" },
  { id: 2, name: "Groceries", kind: "expense", target_amount: null, target_date: null, created_at: "" },
];
const rows: ParsedRow[] = [
  { row_index: 0, date: "2026-05-13", description: "COOP", amount: "-45.30", kind_hint: "expense", is_duplicate: false, errors: [] },
  { row_index: 1, date: "2026-05-13", description: "Spotify", amount: "-15.95", kind_hint: "expense", is_duplicate: true, errors: [] },
];

describe("ImportPreviewTable", () => {
  it("renders rows and flags duplicates as unticked", () => {
    render(
      <ImportPreviewTable
        rows={rows}
        categories={cats}
        defaultCategoryId={1}
        onSelectionsChange={() => {}}
      />,
    );
    expect(screen.getByText("COOP")).toBeInTheDocument();
    expect(screen.getByText("Spotify")).toBeInTheDocument();
    expect(screen.getByText(/Duplicate/i)).toBeInTheDocument();
    const checks = screen.getAllByRole("checkbox");
    // first non-dupe ticked, second dupe unticked
    expect((checks[0] as HTMLInputElement).checked).toBe(true);
    expect((checks[1] as HTMLInputElement).checked).toBe(false);
  });

  it("emits selections on tick change", () => {
    const onSelectionsChange = vi.fn();
    render(
      <ImportPreviewTable
        rows={rows}
        categories={cats}
        defaultCategoryId={1}
        onSelectionsChange={onSelectionsChange}
      />,
    );
    fireEvent.click(screen.getAllByRole("checkbox")[1]);  // tick the dupe row
    const last = onSelectionsChange.mock.calls.at(-1)![0];
    expect(last.map((s: any) => s.row_index).sort()).toEqual([0, 1]);
  });
});
```

- [ ] **Step 2: Implement ImportPreviewTable**

`frontend/src/components/imports/ImportPreviewTable.tsx`:

```tsx
import { useEffect, useMemo, useState } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import type { Category, ImportCommitRowSelection, ParsedRow } from "@/api/types";
import { cn } from "@/lib/utils";

interface Props {
  rows: ParsedRow[];
  categories: Category[];
  defaultCategoryId: number;
  onSelectionsChange: (sel: ImportCommitRowSelection[]) => void;
}

export function ImportPreviewTable({
  rows, categories, defaultCategoryId, onSelectionsChange,
}: Props) {
  const initialTicked = useMemo(
    () => new Set(rows.filter((r) => !r.is_duplicate && r.errors.length === 0).map((r) => r.row_index)),
    [rows],
  );
  const initialCatId = useMemo(() => {
    const m = new Map<number, number>();
    for (const r of rows) m.set(r.row_index, defaultCategoryId);
    return m;
  }, [rows, defaultCategoryId]);

  const [ticked, setTicked] = useState<Set<number>>(initialTicked);
  const [catByRow, setCatByRow] = useState<Map<number, number>>(initialCatId);

  useEffect(() => {
    const sel: ImportCommitRowSelection[] = [];
    for (const r of rows) {
      if (!ticked.has(r.row_index)) continue;
      sel.push({
        row_index: r.row_index,
        category_id: catByRow.get(r.row_index) ?? defaultCategoryId,
        is_recurring: false,
      });
    }
    onSelectionsChange(sel);
  }, [ticked, catByRow, rows, defaultCategoryId, onSelectionsChange]);

  function toggleRow(idx: number) {
    setTicked((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }
  function setRowCat(idx: number, catId: number) {
    setCatByRow((prev) => new Map(prev).set(idx, catId));
  }

  return (
    <div className="space-y-2">
      <BulkBar
        categories={categories}
        tickedCount={ticked.size}
        onBulkCategory={(catId) => {
          setCatByRow((prev) => {
            const next = new Map(prev);
            for (const idx of ticked) next.set(idx, catId);
            return next;
          });
        }}
      />
      <div className="border rounded-md overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-muted">
          <tr>
            <th className="p-2 text-left w-8">
              <Checkbox
                aria-label="Select all ticked rows"
                checked={ticked.size > 0 && ticked.size === rows.filter((r) => r.errors.length === 0 && r.amount !== null).length}
                onCheckedChange={(c) => {
                  if (c) {
                    setTicked(new Set(rows.filter((r) => r.errors.length === 0 && r.amount !== null).map((r) => r.row_index)));
                  } else {
                    setTicked(new Set());
                  }
                }}
              />
            </th>
            <th className="p-2 text-left">Date</th>
            <th className="p-2 text-left">Description</th>
            <th className="p-2 text-right">Amount</th>
            <th className="p-2 text-left">Category</th>
            <th className="p-2 text-left">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const isTicked = ticked.has(r.row_index);
            return (
              <tr
                key={r.row_index}
                className={cn("border-t", r.is_duplicate && "opacity-60", r.errors.length > 0 && "bg-destructive/10")}
              >
                <td className="p-2">
                  <Checkbox
                    checked={isTicked}
                    onCheckedChange={() => toggleRow(r.row_index)}
                    disabled={r.errors.length > 0 || r.amount === null || r.date === null}
                  />
                </td>
                <td className="p-2">{r.date ?? "—"}</td>
                <td className="p-2">{r.description}</td>
                <td className="p-2 text-right tabular-nums">{r.amount ?? "—"}</td>
                <td className="p-2">
                  <Select
                    value={String(catByRow.get(r.row_index) ?? defaultCategoryId)}
                    onValueChange={(v) => setRowCat(r.row_index, Number(v))}
                  >
                    <SelectTrigger className="h-8 w-40"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {categories.map((c) => (
                        <SelectItem key={c.id} value={String(c.id)}>
                          {c.name} ({c.kind})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </td>
                <td className="p-2 text-xs">
                  {r.errors.length > 0 ? (
                    <span className="text-destructive">{r.errors[0]}</span>
                  ) : r.is_duplicate ? (
                    <span className="text-muted-foreground">Duplicate</span>
                  ) : (
                    <span className="text-emerald-600 dark:text-emerald-500">New</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>
    </div>
  );
}

function BulkBar({
  categories, tickedCount, onBulkCategory,
}: {
  categories: Category[];
  tickedCount: number;
  onBulkCategory: (catId: number) => void;
}) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-muted-foreground">{tickedCount} ticked</span>
      <span className="text-muted-foreground">·</span>
      <span>Set category for all ticked:</span>
      <Select onValueChange={(v) => onBulkCategory(Number(v))}>
        <SelectTrigger className="h-8 w-44">
          <SelectValue placeholder="— pick —" />
        </SelectTrigger>
        <SelectContent>
          {categories.map((c) => (
            <SelectItem key={c.id} value={String(c.id)}>
              {c.name} ({c.kind})
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
```

(Verify `frontend/src/components/ui/checkbox.tsx` exists; if not: `npx shadcn@latest add checkbox`.)

- [ ] **Step 3: Build out ImportPage**

Replace `frontend/src/pages/ImportPage.tsx`:

```tsx
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CsvHelpPanel } from "@/components/imports/CsvHelpPanel";
import { ImportConfigPanel } from "@/components/imports/ImportConfigPanel";
import { ImportPreviewTable } from "@/components/imports/ImportPreviewTable";
import { useCategories, useCreateCategory } from "@/hooks/queries/useCategories";
import { previewCsv, commitImport } from "@/api/csv-import";
import type {
  CsvImportConfig, ImportCommitRowSelection, ParsedRow,
} from "@/api/types";

const DEFAULT_CONFIG: CsvImportConfig = {
  delimiter: ";", decimal_sep: ".", thousands_sep: "",
  date_format: "%Y-%m-%d", skip_header_rows: 0, has_header: false,
  amount_format: "signed", sign_convention: "negative_is_expense",
  cols: { date: 0, description: 1, amount: 2 },
};

export default function ImportPage() {
  const { data: categories } = useCategories();
  const createCategory = useCreateCategory();

  const [fileContent, setFileContent] = useState<string | null>(null);
  const [config, setConfig] = useState<CsvImportConfig>(DEFAULT_CONFIG);
  const [rows, setRows] = useState<ParsedRow[] | null>(null);
  const [selections, setSelections] = useState<ImportCommitRowSelection[]>([]);
  const [committing, setCommitting] = useState(false);

  async function handleFile(f: File) {
    const text = await f.text();
    setFileContent(text);
    setRows(null);
  }

  async function ensureImportedCategory(): Promise<number> {
    const existing = (categories ?? []).find((c) => c.name === "Imported");
    if (existing) return existing.id;
    const created = await createCategory.mutateAsync({ name: "Imported", kind: "expense" });
    return created.id;
  }

  async function handlePreview() {
    if (!fileContent) return;
    try {
      const r = await previewCsv(fileContent, config);
      setRows(r.rows);
    } catch (e: any) {
      toast.error(e?.message ?? "Preview failed");
    }
  }

  async function handleCommit() {
    if (!fileContent || selections.length === 0) return;
    setCommitting(true);
    try {
      const r = await commitImport(fileContent, config, selections);
      toast.success(`Imported ${r.imported}, skipped ${r.skipped}`);
      setRows(null);
      setFileContent(null);
    } catch (e: any) {
      toast.error(e?.message ?? "Import failed");
    } finally {
      setCommitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Import</h2>

      <CsvHelpPanel />

      <Card>
        <CardHeader><CardTitle>1. Upload</CardTitle></CardHeader>
        <CardContent>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
          {fileContent && (
            <p className="text-xs text-muted-foreground mt-2">
              Loaded {fileContent.split("\n").length} lines.
            </p>
          )}
        </CardContent>
      </Card>

      {fileContent && (
        <Card>
          <CardHeader><CardTitle>2. Configure</CardTitle></CardHeader>
          <CardContent>
            <ImportConfigPanel config={config} onChange={setConfig} />
            <div className="mt-4">
              <Button onClick={handlePreview}>Preview</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {rows && categories && (
        <Card>
          <CardHeader><CardTitle>3. Review & import</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <ImportPreviewTable
              rows={rows}
              categories={categories}
              defaultCategoryId={categories.find((c) => c.name === "Imported")?.id ?? categories[0]?.id ?? 0}
              onSelectionsChange={setSelections}
            />
            <div className="flex items-center justify-between text-sm">
              <span>
                {selections.length} selected ·{" "}
                {rows.filter((r) => r.is_duplicate).length} duplicates ·{" "}
                {rows.filter((r) => r.errors.length > 0).length} errors
              </span>
              <Button
                onClick={async () => { await ensureImportedCategory(); await handleCommit(); }}
                disabled={selections.length === 0 || committing}
              >
                {committing ? "Importing…" : `Import ${selections.length}`}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run frontend tests**

Run: `npm test`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/imports/ImportPreviewTable.tsx frontend/src/components/imports/ImportPreviewTable.test.tsx frontend/src/pages/ImportPage.tsx frontend/src/components/ui/checkbox.tsx
git commit -m "feat(frontend): ImportPreviewTable + ImportPage end-to-end"
```

---

## Task 22: Preset save/load (PresetSelector)

**Files:**
- Create: `frontend/src/components/imports/PresetSelector.tsx`
- Modify: `frontend/src/pages/ImportPage.tsx` to wire it in

- [ ] **Step 1: Write a smoke test (optional but recommended)**

`frontend/src/components/imports/PresetSelector.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PresetSelector } from "./PresetSelector";
import type { CsvImportConfig } from "@/api/types";

const config: CsvImportConfig = {
  delimiter: ";", decimal_sep: ".", thousands_sep: "",
  date_format: "%Y-%m-%d", skip_header_rows: 0, has_header: false,
  amount_format: "signed", sign_convention: "negative_is_expense",
  cols: { date: 0, description: 1, amount: 2 },
};

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{node}</QueryClientProvider>;
}

describe("PresetSelector", () => {
  it("renders 'Save as preset' control", () => {
    render(wrap(<PresetSelector currentConfig={config} onLoad={() => {}} />));
    expect(screen.getByText(/save as preset/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Implement PresetSelector**

`frontend/src/components/imports/PresetSelector.tsx`:

```tsx
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  useCreateImportPreset, useDeleteImportPreset, useImportPresets,
} from "@/hooks/queries/useImportPresets";
import type { CsvImportConfig } from "@/api/types";

interface Props {
  currentConfig: CsvImportConfig;
  onLoad: (config: CsvImportConfig) => void;
}

export function PresetSelector({ currentConfig, onLoad }: Props) {
  const { data: presets } = useImportPresets();
  const create = useCreateImportPreset();
  const remove = useDeleteImportPreset();

  const [selectedId, setSelectedId] = useState<string>("");
  const [newName, setNewName] = useState("");

  function handleLoad(idStr: string) {
    setSelectedId(idStr);
    const p = (presets ?? []).find((x) => x.id === Number(idStr));
    if (p) onLoad(p.config);
  }

  async function handleSave() {
    if (!newName.trim()) {
      toast.error("Name required");
      return;
    }
    try {
      await create.mutateAsync({ name: newName.trim(), config: currentConfig });
      toast.success(`Preset '${newName}' saved`);
      setNewName("");
    } catch (e: any) {
      toast.error(e?.message ?? "Save failed");
    }
  }

  async function handleDelete() {
    if (!selectedId) return;
    await remove.mutateAsync(Number(selectedId));
    setSelectedId("");
    toast.success("Preset deleted");
  }

  return (
    <div className="flex items-end gap-2 flex-wrap">
      <div className="space-y-1">
        <div className="text-xs text-muted-foreground">Load preset</div>
        <Select value={selectedId} onValueChange={handleLoad}>
          <SelectTrigger className="w-44"><SelectValue placeholder="—" /></SelectTrigger>
          <SelectContent>
            {(presets ?? []).map((p) => (
              <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Button type="button" variant="ghost" disabled={!selectedId} onClick={handleDelete}>
        Delete
      </Button>

      <div className="space-y-1 ml-auto">
        <div className="text-xs text-muted-foreground">Save current config as preset</div>
        <div className="flex gap-2">
          <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="UBS" className="w-32" />
          <Button type="button" onClick={handleSave} disabled={create.isPending}>
            {create.isPending ? "Saving…" : "Save as preset"}
          </Button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Wire into ImportPage**

In `frontend/src/pages/ImportPage.tsx`, inside the `Configure` Card, above `ImportConfigPanel`:

```tsx
import { PresetSelector } from "@/components/imports/PresetSelector";

// ... inside the Configure Card body, before ImportConfigPanel:
<PresetSelector currentConfig={config} onLoad={setConfig} />
<div className="my-3 border-t" />
```

- [ ] **Step 4: Run frontend tests**

Run: `npm test`
Expected: all PASS.

- [ ] **Step 5: Manual smoke (developer mode)**

Run: `cd frontend; npm run dev:all`. In the browser:
1. Visit /import
2. Click "What should my CSV look like?" — both example tables render
3. Upload a small CSV, set config, Preview — preview table renders
4. Tick / untick rows, change category per row
5. Click "Import N" — toast confirms; transactions appear on /transactions
6. Save current config as preset "UBS"
7. Refresh the page, load preset "UBS" — config restored

If any step fails, capture details and fix before committing.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/imports/PresetSelector.tsx frontend/src/components/imports/PresetSelector.test.tsx frontend/src/pages/ImportPage.tsx
git commit -m "feat(frontend): PresetSelector — save/load/delete import presets"
```

---

## Whole-feature smoke checklist (post-Section-A through Section-E)

Run after all 22 tasks:

- [ ] `cd backend; pytest -v` — all backend tests green (target ≥ 95)
- [ ] `cd frontend; npm test` — all frontend tests green (target ≥ 50)
- [ ] `cd frontend; npx tsc --noEmit` — no type errors
- [ ] Manual dashboard walk:
  - Create one category of each kind (income, expense, savings with target)
  - Create a few expense transactions, an income transaction, a savings deposit and withdrawal
  - Verify: KpiRow shows Income / Expense / Net / Saved with correct values
  - Savings goal card shows progress + days-left
  - BudgetWidget shows per-category rows with correct color thresholds; overall progress + remaining
  - Donut excludes savings (only expense categories appear)
  - Sidebar has Import nav item
  - 3-segment theme toggle in header — all three themes apply correctly; persist across refresh
  - Tab title is "Financial Assistant"; favicon shows "Fr." in a circle
- [ ] Manual import walk:
  - /import help panel renders both layout examples
  - Upload a CSV, configure, preview, fix categories, import
  - Verify duplicates are flagged and unticked by default
  - Save preset, reload page, load preset — config restored
- [ ] Commit any stray fixes from the smoke walk; tag this as a feature checkpoint:

```bash
git tag phase3-complete
```

---

## Notes for executor

- The `Imported` category is auto-created on first import. After a few imports it may accumulate uncategorized transactions; the user can reclassify on /transactions.
- The CSV parser tolerates malformed rows by flagging errors on the row rather than aborting the whole file. This is intentional — partial imports are normal.
- `parse_csv` produces 0-based `row_index` AFTER skipping headers, so `selections[].row_index` aligns with what the preview table shows.
- Withdrawals from savings are negative-amount transactions. The TransactionFormDialog Deposit/Withdraw toggle signs the amount at submit; the API receives the signed value.
- BudgetWidget reuses `useBudgetsForMonth` which already returns `BudgetWithSpending` rows (`category_id, category_name, monthly_limit, spent, over_budget, overage`). No backend change needed for Section B.
- If `useTransactions({})` (with no month filter) doesn't fetch all transactions today, extend the API client to omit the `month` query param when not provided. The SavingsGoalsRow needs cumulative totals, not month-scoped.
- Tests use `userId=1` per the existing `dependencies.get_current_user_id` override.
