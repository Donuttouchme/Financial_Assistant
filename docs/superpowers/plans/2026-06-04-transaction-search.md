# Transaction Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an always-visible search box to the global header that finds transactions across *all* months by description or category name (Hungarian-accent-correct), rendering results on the Transactions page.

**Architecture:** A new `GET /api/transactions/search?q=` endpoint backed by a `transaction_service.search_transactions` function that filters in Python with `str.casefold()` (so accented Hungarian text folds correctly — SQLite `LIKE`/`lower()` only fold ASCII). On the frontend, the search term lives in the URL (`?q=`). A search box in the global `Header` debounces input (300 ms) and navigates to `/transactions?q=term` once the trimmed term reaches 2 characters; while a search is active the header's month picker is disabled and the Transactions page hides its category dropdown and shows all-months results. A small `useActiveSearch()` hook (`?q=` trimmed, ≥2 chars → term | null) is the single source of truth shared by the header and the page.

**Tech Stack:** Backend — FastAPI, SQLAlchemy 2.0, SQLite, pytest. Frontend — React 18 + TS, TanStack Query v5, react-router-dom 6, shadcn-ui, Vitest 2 + MSW 2.

---

## Behavior summary (the contract this plan implements)

1. Global header gets an always-visible search input beside the month picker.
2. Typing debounces 300 ms (history *push*); once the trimmed term is ≥2 chars it navigates to `/transactions?q=term`. Below 2 chars (or cleared) it drops `?q=`.
3. While `?q=` is an active search: the header month picker is disabled; the Transactions page hides its category dropdown; results span **all months**.
4. Match = `description` **OR** category name contains the term, case-insensitive via `str.casefold()`.
5. Returns **all** matches, ordered `date desc, id desc`, no limit.
6. Clearing the box returns to the normal month + category view.

## File structure

**Backend**
- Modify `backend/app/services/transaction_service.py` — add `search_transactions(db, *, user_id, q)`.
- Modify `backend/app/routers/transactions.py` — add `GET /api/transactions/search`.
- Modify `backend/tests/test_transaction_service.py` — service tests.
- Modify `backend/tests/test_routes/test_transactions.py` — route tests.

**Frontend**
- Create `frontend/src/hooks/useDebouncedValue.ts` — generic debounce hook.
- Create `frontend/src/hooks/useActiveSearch.ts` — `?q=` → term | null (≥2 chars, trimmed).
- Create `frontend/src/hooks/__tests__/useDebouncedValue.test.tsx`
- Create `frontend/src/hooks/__tests__/useActiveSearch.test.tsx`
- Modify `frontend/src/api/transactions.ts` — add `searchTransactions(q)`.
- Modify `frontend/src/hooks/queries/useTransactions.ts` — add `useSearchTransactions` + `enabled` option on `useTransactions`.
- Create `frontend/src/hooks/queries/__tests__/useSearchTransactions.test.tsx`
- Modify `frontend/src/tests/handlers.ts` — MSW handler for `/api/transactions/search`.
- Modify `frontend/src/components/transactions/TransactionsTable.tsx` — `search` prop, dual hooks, search empty message.
- Create `frontend/src/components/transactions/__tests__/TransactionsTable.test.tsx`
- Modify `frontend/src/pages/TransactionsPage.tsx` — header text + hide category dropdown while searching.
- Modify `frontend/src/components/layout/Header.tsx` — search input, debounced navigation, disable month picker while searching.
- Create `frontend/src/components/layout/__tests__/Header.test.tsx`

## Commands reference

- Backend tests (PowerShell, from repo root): `cd backend; .\.venv\Scripts\python.exe -m pytest -q <path>; cd ..`
- Frontend tests (from repo root): `cd frontend; npm test -- --run <path>; cd ..`
- Frontend typecheck/build: `cd frontend; npm run build; cd ..`
- Baseline before starting: backend 230 passing, frontend 145 passing.

---

### Task 1: Backend `search_transactions` service

**Files:**
- Modify: `backend/app/services/transaction_service.py` (add function after `list_transactions`, around line 184)
- Test: `backend/tests/test_transaction_service.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_transaction_service.py`:

```python
def test_search_matches_description_case_insensitive(db_session):
    from app.models.category import Category
    from app.services import transaction_service as svc

    cat = Category(user_id=1, name="Food", kind="expense")
    db_session.add(cat)
    db_session.commit()
    svc.create_transaction(
        db_session, user_id=1, amount=Decimal("10"),
        tx_date=date(2026, 1, 5), category_id=cat.id,
        description="Lunch at Joe", currency="CHF",
    )
    results = svc.search_transactions(db_session, user_id=1, q="LUNCH")
    assert [t.description for t in results] == ["Lunch at Joe"]


def test_search_matches_accented_text_with_casefold(db_session):
    # SQLite LIKE/lower() would FAIL this (ASCII-only folding); casefold passes.
    from app.models.category import Category
    from app.services import transaction_service as svc

    cat = Category(user_id=1, name="Food", kind="expense")
    db_session.add(cat)
    db_session.commit()
    svc.create_transaction(
        db_session, user_id=1, amount=Decimal("10"),
        tx_date=date(2026, 1, 5), category_id=cat.id,
        description="Étterem belváros", currency="CHF",
    )
    results = svc.search_transactions(db_session, user_id=1, q="ÉTTEREM")
    assert len(results) == 1


def test_search_matches_category_name(db_session):
    from app.models.category import Category
    from app.services import transaction_service as svc

    cat = Category(user_id=1, name="Groceries", kind="expense")
    db_session.add(cat)
    db_session.commit()
    svc.create_transaction(
        db_session, user_id=1, amount=Decimal("10"),
        tx_date=date(2026, 1, 5), category_id=cat.id,
        description="weekly shop", currency="CHF",
    )
    results = svc.search_transactions(db_session, user_id=1, q="grocer")
    assert len(results) == 1


def test_search_ignores_month_and_orders_date_desc(db_session):
    from app.models.category import Category
    from app.services import transaction_service as svc

    cat = Category(user_id=1, name="Shopping", kind="expense")
    db_session.add(cat)
    db_session.commit()
    svc.create_transaction(
        db_session, user_id=1, amount=Decimal("10"),
        tx_date=date(2026, 1, 5), category_id=cat.id,
        description="amazon jan", currency="CHF",
    )
    svc.create_transaction(
        db_session, user_id=1, amount=Decimal("20"),
        tx_date=date(2026, 5, 5), category_id=cat.id,
        description="amazon may", currency="CHF",
    )
    results = svc.search_transactions(db_session, user_id=1, q="amazon")
    assert [t.description for t in results] == ["amazon may", "amazon jan"]


def test_search_short_query_returns_empty(db_session):
    from app.models.category import Category
    from app.services import transaction_service as svc

    cat = Category(user_id=1, name="Food", kind="expense")
    db_session.add(cat)
    db_session.commit()
    svc.create_transaction(
        db_session, user_id=1, amount=Decimal("10"),
        tx_date=date(2026, 1, 5), category_id=cat.id,
        description="ab cd", currency="CHF",
    )
    assert svc.search_transactions(db_session, user_id=1, q="a") == []
    assert svc.search_transactions(db_session, user_id=1, q="  ") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest -q tests/test_transaction_service.py -k search; cd ..`
Expected: FAIL with `AttributeError: module 'app.services.transaction_service' has no attribute 'search_transactions'`.

- [ ] **Step 3: Implement `search_transactions`**

In `backend/app/services/transaction_service.py`, add this function immediately after `list_transactions` (after line 184):

```python
def search_transactions(
    db: Session,
    *,
    user_id: int,
    q: str,
) -> list[Transaction]:
    """All-months search: case-insensitive substring of the query against the
    transaction description OR its category name.

    Matching is done in Python with str.casefold() rather than SQL LIKE because
    SQLite's LIKE/lower() only fold ASCII case — accented Hungarian letters
    (á/é/ő/ű ...) would not match across case. Data volume is single-user and
    modest, so loading the rows and filtering in Python is cheap.

    Returns [] for queries shorter than 2 non-whitespace chars (defensive; the
    frontend gates at 2 chars too).
    """
    term = q.strip().casefold()
    if len(term) < 2:
        return []

    cat_names = {
        c.id: c.name
        for c in db.execute(
            select(Category).where(Category.user_id == user_id)
        ).scalars().all()
    }

    stmt = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
    )
    rows = db.execute(stmt).scalars().all()

    out: list[Transaction] = []
    for t in rows:
        description = (t.description or "").casefold()
        category = cat_names.get(t.category_id, "").casefold()
        if term in description or term in category:
            out.append(t)
    return out
```

(`select` and `Category` are already imported at the top of the file.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest -q tests/test_transaction_service.py -k search; cd ..`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/transaction_service.py backend/tests/test_transaction_service.py
git commit -m "feat(backend): add transaction_service.search_transactions (casefold, all-months)"
```

---

### Task 2: Backend `GET /api/transactions/search` route

**Files:**
- Modify: `backend/app/routers/transactions.py` (add route after `list_transactions`, after line 46)
- Test: `backend/tests/test_routes/test_transactions.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_routes/test_transactions.py`:

```python
def test_search_endpoint_returns_enriched_matches(client):
    cat = client.post("/api/categories", json={"name": "Food"}).json()["id"]
    client.post("/api/transactions", json={
        "amount": "10", "date": "2026-01-05", "category_id": cat,
        "description": "Lunch", "currency": "CHF",
    })
    client.post("/api/transactions", json={
        "amount": "20", "date": "2026-05-05", "category_id": cat,
        "description": "Dinner", "currency": "CHF",
    })

    resp = client.get("/api/transactions/search", params={"q": "lun"})
    assert resp.status_code == 200
    body = resp.json()
    assert [t["description"] for t in body] == ["Lunch"]
    assert "base_amount" in body[0]


def test_search_endpoint_short_query_returns_empty(client):
    resp = client.get("/api/transactions/search", params={"q": "a"})
    assert resp.status_code == 200
    assert resp.json() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest -q tests/test_routes/test_transactions.py -k search; cd ..`
Expected: FAIL — the `/search` path falls through to a 404 (no such route) or 405, so the assertions fail.

- [ ] **Step 3: Implement the route**

In `backend/app/routers/transactions.py`, add this handler immediately after the `list_transactions` function (after line 46):

```python
@router.get("/search", response_model=list[TransactionRead])
def search_transactions(
    q: str = Query(default=""),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    txs = transaction_service.search_transactions(db, user_id=user_id, q=q)
    return transaction_service.enrich_with_base_amount(db, txs)
```

(`Query`, `transaction_service`, and `TransactionRead` are already imported.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest -q tests/test_routes/test_transactions.py -k search; cd ..`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/transactions.py backend/tests/test_routes/test_transactions.py
git commit -m "feat(backend): add GET /api/transactions/search endpoint"
```

---

### Task 3: `useDebouncedValue` hook

**Files:**
- Create: `frontend/src/hooks/useDebouncedValue.ts`
- Test: `frontend/src/hooks/__tests__/useDebouncedValue.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/hooks/__tests__/useDebouncedValue.test.tsx`:

```tsx
import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";

afterEach(() => vi.useRealTimers());

describe("useDebouncedValue", () => {
  it("returns the latest value only after the delay elapses", () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(
      ({ v }) => useDebouncedValue(v, 300),
      { initialProps: { v: "a" } },
    );
    expect(result.current).toBe("a");

    rerender({ v: "ab" });
    expect(result.current).toBe("a"); // not yet — timer pending

    act(() => vi.advanceTimersByTime(300));
    expect(result.current).toBe("ab");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend; npm test -- --run src/hooks/__tests__/useDebouncedValue.test.tsx; cd ..`
Expected: FAIL — cannot resolve module `@/hooks/useDebouncedValue`.

- [ ] **Step 3: Implement the hook**

Create `frontend/src/hooks/useDebouncedValue.ts`:

```ts
import { useEffect, useState } from "react";

/** Returns `value` delayed by `delayMs`, resetting the timer on each change. */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend; npm test -- --run src/hooks/__tests__/useDebouncedValue.test.tsx; cd ..`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useDebouncedValue.ts frontend/src/hooks/__tests__/useDebouncedValue.test.tsx
git commit -m "feat(frontend): add useDebouncedValue hook"
```

---

### Task 4: `useActiveSearch` hook

**Files:**
- Create: `frontend/src/hooks/useActiveSearch.ts`
- Test: `frontend/src/hooks/__tests__/useActiveSearch.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/hooks/__tests__/useActiveSearch.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useActiveSearch } from "@/hooks/useActiveSearch";

function wrap(initial: string) {
  return ({ children }: { children: React.ReactNode }) => (
    <MemoryRouter initialEntries={[initial]}>{children}</MemoryRouter>
  );
}

describe("useActiveSearch", () => {
  it("returns the trimmed term for >= 2 chars", () => {
    const { result } = renderHook(() => useActiveSearch(), {
      wrapper: wrap("/transactions?q=%20ab%20"),
    });
    expect(result.current).toBe("ab");
  });

  it("returns null below 2 chars", () => {
    const { result } = renderHook(() => useActiveSearch(), {
      wrapper: wrap("/transactions?q=a"),
    });
    expect(result.current).toBeNull();
  });

  it("returns null when q is missing", () => {
    const { result } = renderHook(() => useActiveSearch(), {
      wrapper: wrap("/transactions"),
    });
    expect(result.current).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend; npm test -- --run src/hooks/__tests__/useActiveSearch.test.tsx; cd ..`
Expected: FAIL — cannot resolve module `@/hooks/useActiveSearch`.

- [ ] **Step 3: Implement the hook**

Create `frontend/src/hooks/useActiveSearch.ts`:

```ts
import { useSearchParams } from "react-router-dom";

/**
 * Single source of truth for "is a search active": reads ?q=, trims it, and
 * returns the term only once it has >= 2 characters, else null. Shared by the
 * global Header (to disable the month picker) and the Transactions page.
 */
export function useActiveSearch(): string | null {
  const [params] = useSearchParams();
  const term = (params.get("q") ?? "").trim();
  return term.length >= 2 ? term : null;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend; npm test -- --run src/hooks/__tests__/useActiveSearch.test.tsx; cd ..`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useActiveSearch.ts frontend/src/hooks/__tests__/useActiveSearch.test.tsx
git commit -m "feat(frontend): add useActiveSearch hook"
```

---

### Task 5: MSW handler for the search endpoint

**Files:**
- Modify: `frontend/src/tests/handlers.ts` (add handler after the `GET /api/transactions` handler, after line 153)

This is test infrastructure (no TDD red/green). The mock uses plain `toLowerCase()` — accent-correctness is verified by the *backend* tests (Task 1); the mock only needs to route by description/category substring for frontend tests.

- [ ] **Step 1: Add the handler**

In `frontend/src/tests/handlers.ts`, immediately after the `http.get("/api/transactions", ...)` handler block (after line 153, before the `http.post("/api/transactions", ...)` block), insert:

```ts
  http.get("/api/transactions/search", ({ request }) => {
    const url = new URL(request.url);
    const q = (url.searchParams.get("q") ?? "").trim();
    if (q.length < 2) return HttpResponse.json([]);
    const term = q.toLowerCase();
    const rows = testState.transactions.filter((t) => {
      const desc = (t.description ?? "").toLowerCase();
      const cat = (
        testState.categories.find((c) => c.id === t.category_id)?.name ?? ""
      ).toLowerCase();
      return desc.includes(term) || cat.includes(term);
    });
    return HttpResponse.json(rows);
  }),
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `cd frontend; npm test -- --run src/tests; cd ..`
Expected: PASS (no regressions in existing handler-dependent tests).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/tests/handlers.ts
git commit -m "test(frontend): add MSW handler for /api/transactions/search"
```

---

### Task 6: `searchTransactions` API + `useSearchTransactions` hook + `enabled` on `useTransactions`

**Files:**
- Modify: `frontend/src/api/transactions.ts`
- Modify: `frontend/src/hooks/queries/useTransactions.ts`
- Test: `frontend/src/hooks/queries/__tests__/useSearchTransactions.test.tsx` (create)

- [ ] **Step 1: Write the failing test**

Create `frontend/src/hooks/queries/__tests__/useSearchTransactions.test.tsx`:

```tsx
import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSearchTransactions } from "@/hooks/queries/useTransactions";
import { resetTestState, testState } from "@/tests/handlers";

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

beforeEach(() => {
  resetTestState();
  testState.categories.push({
    id: 1, name: "Food", kind: "expense",
    target_amount: null, target_date: null, created_at: "",
  });
  testState.transactions.push({
    id: 1, user_id: 1, amount: "10", date: "2026-01-05", category_id: 1,
    description: "lunch out", is_recurring: false, currency: "CHF",
    base_amount: "10", created_at: "", updated_at: "",
  });
});

describe("useSearchTransactions", () => {
  it("fetches results matching the term", async () => {
    const { result } = renderHook(() => useSearchTransactions("lun"), {
      wrapper: wrap(),
    });
    await waitFor(() => expect(result.current.data?.length).toBe(1));
    expect(result.current.data?.[0].description).toBe("lunch out");
  });

  it("does not fetch when disabled", () => {
    const { result } = renderHook(
      () => useSearchTransactions("lun", { enabled: false }),
      { wrapper: wrap() },
    );
    expect(result.current.fetchStatus).toBe("idle");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend; npm test -- --run src/hooks/queries/__tests__/useSearchTransactions.test.tsx; cd ..`
Expected: FAIL — `useSearchTransactions` is not exported.

- [ ] **Step 3: Add the API function**

In `frontend/src/api/transactions.ts`, add after `listTransactions` (after line 19):

```ts
export function searchTransactions(q: string): Promise<Transaction[]> {
  const search = new URLSearchParams({ q });
  return apiFetch<Transaction[]>(`/api/transactions/search?${search.toString()}`);
}
```

- [ ] **Step 4: Add the hook and the `enabled` option**

In `frontend/src/hooks/queries/useTransactions.ts`:

First, extend the import on lines 3–6 to include `searchTransactions`:

```ts
import {
  createTransaction, deleteTransaction, listTransactions,
  searchTransactions, updateTransaction,
} from "@/api/transactions";
```

Then replace the existing `useTransactions` function (lines 14–19) with:

```ts
export function useTransactions(
  params: { month?: string; category_id?: number },
  options?: { enabled?: boolean },
) {
  return useQuery<Transaction[]>({
    queryKey: [TX_KEY_ROOT, params.month ?? null, params.category_id ?? null],
    queryFn: () => listTransactions(params),
    enabled: options?.enabled ?? true,
  });
}

export function useSearchTransactions(
  q: string,
  options?: { enabled?: boolean },
) {
  return useQuery<Transaction[]>({
    queryKey: [TX_KEY_ROOT, "search", q],
    queryFn: () => searchTransactions(q),
    enabled: options?.enabled ?? true,
  });
}
```

(The `["transactions", "search", q]` key is prefixed under `TX_KEY_ROOT`, so the existing `invalidateQueries({ queryKey: [TX_KEY_ROOT] })` calls in the create/update/delete mutations automatically refresh search results.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend; npm test -- --run src/hooks/queries/__tests__/useSearchTransactions.test.tsx; cd ..`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/transactions.ts frontend/src/hooks/queries/useTransactions.ts frontend/src/hooks/queries/__tests__/useSearchTransactions.test.tsx
git commit -m "feat(frontend): add useSearchTransactions hook + enabled option"
```

---

### Task 7: `TransactionsTable` search mode + `TransactionsPage` header/dropdown

**Files:**
- Modify: `frontend/src/components/transactions/TransactionsTable.tsx`
- Modify: `frontend/src/pages/TransactionsPage.tsx`
- Test: `frontend/src/components/transactions/__tests__/TransactionsTable.test.tsx` (create)

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/transactions/__tests__/TransactionsTable.test.tsx`:

```tsx
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TransactionsTable } from "../TransactionsTable";
import { resetTestState, testState } from "@/tests/handlers";

function renderTable(props: { month: string; categoryId?: number; search?: string | null }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <TransactionsTable {...props} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  resetTestState();
  testState.categories.push({
    id: 1, name: "Food", kind: "expense",
    target_amount: null, target_date: null, created_at: "",
  });
  testState.transactions.push(
    {
      id: 1, user_id: 1, amount: "10", date: "2026-01-05", category_id: 1,
      description: "lunch out", is_recurring: false, currency: "CHF",
      base_amount: "10", created_at: "", updated_at: "",
    },
    {
      id: 2, user_id: 1, amount: "20", date: "2026-05-05", category_id: 1,
      description: "dinner", is_recurring: false, currency: "CHF",
      base_amount: "20", created_at: "", updated_at: "",
    },
  );
});

describe("TransactionsTable search mode", () => {
  it("renders all-months search matches when search prop is set", async () => {
    renderTable({ month: "2026-05", search: "lun" });
    await waitFor(() =>
      expect(screen.getByText("lunch out")).toBeInTheDocument(),
    );
    expect(screen.queryByText("dinner")).not.toBeInTheDocument();
  });

  it("shows a search-specific empty message when nothing matches", async () => {
    renderTable({ month: "2026-05", search: "zzz" });
    await waitFor(() =>
      expect(screen.getByText(/No transactions match/i)).toBeInTheDocument(),
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend; npm test -- --run src/components/transactions/__tests__/TransactionsTable.test.tsx; cd ..`
Expected: FAIL — `TransactionsTable` does not accept/handle a `search` prop, so the second-month row leaks in (or the wrong endpoint is hit) and the empty message text doesn't appear.

- [ ] **Step 3: Update `TransactionsTable`**

In `frontend/src/components/transactions/TransactionsTable.tsx`:

Replace the import on lines 15–17 with one that also pulls in `useSearchTransactions`:

```tsx
import {
  useTransactions, useSearchTransactions, useDeleteTransaction,
} from "@/hooks/queries/useTransactions";
```

Replace the `Props` interface (lines 23–26) and the start of the component (lines 28–32) with:

```tsx
interface Props {
  month: string;
  categoryId?: number;
  search?: string | null;
}

export function TransactionsTable({ month, categoryId, search }: Props) {
  const isSearching = !!search;
  const listQuery = useTransactions(
    { month, category_id: categoryId },
    { enabled: !isSearching },
  );
  const searchQuery = useSearchTransactions(search ?? "", {
    enabled: isSearching,
  });
  const { data: txs, isLoading } = isSearching ? searchQuery : listQuery;
```

Replace the empty-state block (lines 51–57) with:

```tsx
  if ((txs ?? []).length === 0) {
    return (
      <p className="text-sm text-muted-foreground italic py-8 text-center">
        {isSearching
          ? `No transactions match “${search}”.`
          : "No transactions for this month."}
      </p>
    );
  }
```

- [ ] **Step 4: Update `TransactionsPage`**

In `frontend/src/pages/TransactionsPage.tsx`:

Add the import after line 8 (`import { useCategories } ...`):

```tsx
import { useActiveSearch } from "@/hooks/useActiveSearch";
```

Add the active-search read inside the component, right after line 17 (`const categoryId = ...`):

```tsx
  const search = useActiveSearch();
```

Replace the header `<h2>` (lines 38–40) with:

```tsx
        <h2 className="text-2xl font-semibold">
          {search
            ? `Search results for “${search}”`
            : `Transactions — ${monthLabel(month)}`}
        </h2>
```

Wrap the category-filter `<div className="flex items-end gap-2">` block (lines 41–63) so it only renders when not searching — change the opening line 41 from:

```tsx
        <div className="flex items-end gap-2">
```

to:

```tsx
        {!search && (
        <div className="flex items-end gap-2">
```

and the matching closing `</div>` on line 63 to:

```tsx
        </div>
        )}
```

Finally, pass `search` to the table — replace line 65:

```tsx
      <TransactionsTable month={month} categoryId={categoryId} search={search} />
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend; npm test -- --run src/components/transactions/__tests__/TransactionsTable.test.tsx src/pages/__tests__/TransactionsPage.test.tsx; cd ..`
Expected: PASS (new table tests + existing TransactionsPage test still green).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/transactions/TransactionsTable.tsx frontend/src/pages/TransactionsPage.tsx frontend/src/components/transactions/__tests__/TransactionsTable.test.tsx
git commit -m "feat(frontend): search mode in TransactionsTable + TransactionsPage header"
```

---

### Task 8: Search box in the global `Header` (debounced navigation + month-picker disable)

**Files:**
- Modify: `frontend/src/components/layout/Header.tsx`
- Test: `frontend/src/components/layout/__tests__/Header.test.tsx` (create)

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/layout/__tests__/Header.test.tsx`:

```tsx
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { Header } from "../Header";

function LocationProbe() {
  const loc = useLocation();
  return <div data-testid="loc">{loc.pathname + loc.search}</div>;
}

function renderHeader(initial: string) {
  return render(
    <MemoryRouter initialEntries={[initial]}>
      <Header onAddTransaction={() => {}} />
      <LocationProbe />
    </MemoryRouter>,
  );
}

afterEach(() => vi.useRealTimers());

describe("Header search", () => {
  it("navigates to /transactions?q= after debounce once term >= 2 chars", () => {
    vi.useFakeTimers();
    renderHeader("/dashboard");
    const input = screen.getByLabelText("Search transactions");

    fireEvent.change(input, { target: { value: "etterem" } });
    act(() => vi.advanceTimersByTime(300));

    expect(screen.getByTestId("loc").textContent).toBe("/transactions?q=etterem");
  });

  it("disables the month picker while a search is active", () => {
    renderHeader("/transactions?q=etterem");
    expect(screen.getByRole("combobox")).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend; npm test -- --run src/components/layout/__tests__/Header.test.tsx; cd ..`
Expected: FAIL — there is no input labelled "Search transactions"; `getByLabelText` throws.

- [ ] **Step 3: Rewrite `Header.tsx`**

Replace the entire contents of `frontend/src/components/layout/Header.tsx` with:

```tsx
import { useEffect, useState } from "react";
import { Plus, Search } from "lucide-react";
import { useNavigate, useLocation, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useUrlMonth } from "@/hooks/useUrlMonth";
import { useActiveSearch } from "@/hooks/useActiveSearch";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { monthOptions } from "@/lib/date";
import { ThemeToggle } from "./ThemeToggle";

interface HeaderProps {
  onAddTransaction: () => void;
}

export function Header({ onAddTransaction }: HeaderProps) {
  const { month, setMonth } = useUrlMonth();
  const opts = monthOptions();
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  const activeSearch = useActiveSearch();

  const urlQ = params.get("q") ?? "";
  const [text, setText] = useState(urlQ);
  const debounced = useDebouncedValue(text, 300);

  // Keep the box in sync when ?q= changes from outside (back button, clearing).
  useEffect(() => {
    setText(urlQ);
  }, [urlQ]);

  // Push the debounced term into the URL. >= 2 chars -> /transactions?q=term;
  // otherwise drop an existing ?q=. No-op on non-transactions pages with no q.
  useEffect(() => {
    const term = debounced.trim();
    if (term.length >= 2) {
      const target = `/transactions?q=${encodeURIComponent(term)}`;
      if (location.pathname + location.search !== target) {
        navigate(target);
      }
    } else if (params.get("q")) {
      navigate("/transactions");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

  return (
    <header className="h-14 border-b bg-card flex items-center justify-between px-4">
      <div className="flex items-center gap-2">
        <Select
          value={month}
          onValueChange={setMonth}
          disabled={activeSearch !== null}
        >
          <SelectTrigger
            className="w-40"
            title={
              activeSearch !== null
                ? "Clear search to pick a month"
                : undefined
            }
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {opts.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="relative w-64">
          <Search className="pointer-events-none absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            aria-label="Search transactions"
            placeholder="Search transactions…"
            className="pl-8"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") setText("");
            }}
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <ThemeToggle />
        <Button onClick={onAddTransaction} size="sm">
          <Plus className="h-4 w-4 mr-1" />
          Add transaction
        </Button>
      </div>
    </header>
  );
}
```

Notes for the implementer:
- `type="search"` gives the native clear (×) affordance for free; `Escape` also clears. Clearing empties `text` → debounced becomes empty → the effect drops `?q=`.
- The month picker is disabled (not hidden) while a search is active, with a tooltip explaining why.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend; npm test -- --run src/components/layout/__tests__/Header.test.tsx; cd ..`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/Header.tsx frontend/src/components/layout/__tests__/Header.test.tsx
git commit -m "feat(frontend): global header search box with debounced navigation"
```

---

### Task 9: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend suite**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest -q; cd ..`
Expected: PASS — 230 prior + 7 new = 237 passed.

- [ ] **Step 2: Run the full frontend suite**

Run: `cd frontend; npm test -- --run; cd ..`
Expected: PASS — 145 prior + new tests, all green.

- [ ] **Step 3: Typecheck + production build**

Run: `cd frontend; npm run build; cd ..`
Expected: `tsc -b` clean (no type errors), `vite build` succeeds.

- [ ] **Step 4: Manual smoke (optional, recommended)**

Launch the app, type "etterem" (or any 2+ char term) in the header search box from any page. Expect: navigation to `/transactions?q=etterem`, the month picker greys out, the page header reads "Search results for …", and the category dropdown is hidden. Clear the box (× or Esc): you return to the month view and the month picker re-enables.

- [ ] **Step 5: Commit any incidental lockfile/formatting churn (if present)**

```bash
git status --short
# only if there is unintended churn:
git checkout frontend/package-lock.json
```

---

## Self-review notes

- **Spec coverage:** scope (all months) → Task 1/2; match fields (desc OR category name) → Task 1; case-folding for Hungarian → Task 1 (`test_search_matches_accented_text_with_casefold`); URL `?q=` state → Task 4/8; debounce 300 ms + push history → Task 3/8; volume (all matches) → Task 1 (no LIMIT); new `/search` endpoint → Task 2; table dual-hook wiring → Task 6/7; activation ≥2 chars → Task 4 (frontend gate) + Task 1 (backend guard); month picker disabled while searching → Task 8; search box in global header, always visible, typing navigates to Transactions → Task 8.
- **Type consistency:** `search_transactions(db, *, user_id, q)` used identically in service (Task 1) and router (Task 2). `useSearchTransactions(q, options?)` and `useTransactions(params, options?)` signatures defined in Task 6 and consumed in Task 7. `search?: string | null` prop on `TransactionsTable` defined in Task 7 and supplied by `TransactionsPage` (which gets it from `useActiveSearch(): string | null`, Task 4).
- **Out of scope (not built):** amount/numeric search, accent-stripping/fuzzy match, pagination, a `Ctrl+K`/`/` focus shortcut.
