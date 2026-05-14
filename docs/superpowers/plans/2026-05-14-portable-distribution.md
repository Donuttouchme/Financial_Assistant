# Portable Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Financial Assistant to a non-technical Windows user as a signed-looking Inno Setup installer that puts the DB in `%APPDATA%`, with auto-idle backend shutdown, port-reuse on relaunch, and an empty-state UX that guides first-run.

**Architecture:** Single codebase serves both the dev's existing setup (env var unset → DB stays at `backend/financial.db`) and the portable build (launcher sets `FA_DB_PATH=%APPDATA%\FinancialAssistant\financial.db`). Frontend sends a heartbeat every 5 min while the tab is open; a backend asyncio watchdog raises SIGINT after 60 min without any request, letting uvicorn shut down gracefully. The Inno Setup installer wraps an embedded Python interpreter plus pre-installed wheels into a single `.exe` that the recipient runs once and forgets about.

**Tech Stack:** FastAPI, SQLAlchemy 2.0.49, pydantic-settings, React 18 + TanStack Query 5, Recharts, Inno Setup 6 (Pascal-style scripting), PowerShell 5.1, Python 3.14 embeddable distribution from python.org, GitHub Releases via `gh` CLI.

---

## File Structure

**Backend (modified):**
- `backend/app/config.py` — add `fa_db_path` field + `resolved_database_url()` helper
- `backend/app/database.py` — use `settings.resolved_database_url()`
- `backend/app/main.py` — wire heartbeat router, last-activity middleware, idle watchdog lifespan task
- `backend/app/idle.py` — NEW. Module-level `last_activity` timestamp + async `idle_watchdog()` task
- `backend/app/routers/heartbeat.py` — NEW. `POST /api/heartbeat`

**Backend tests:**
- `backend/tests/test_config.py` — NEW. `resolved_database_url()` env-var handling
- `backend/tests/test_heartbeat.py` — NEW. endpoint shape + middleware bumps `last_activity`
- `backend/tests/test_idle_watchdog.py` — NEW. mocked time + mocked signal, asserts trigger logic

**Frontend (new):**
- `frontend/src/api/heartbeat.ts` — NEW. `postHeartbeat()` fetch helper
- `frontend/src/hooks/useHeartbeat.ts` — NEW. `setInterval` calling heartbeat every 5 min
- `frontend/src/components/EmptyAppState.tsx` — NEW. Reusable empty-state card

**Frontend (modified):**
- `frontend/src/App.tsx` — call `useHeartbeat()`
- `frontend/src/pages/DashboardPage.tsx` — render `EmptyAppState` when `categories.length === 0`
- `frontend/src/pages/TransactionsPage.tsx` — same
- `frontend/src/pages/BudgetsPage.tsx` — same
- `frontend/src/components/dashboard/CategoryDonut.tsx` — custom legend always shows `name (pct%)`
- `frontend/src/tests/handlers.ts` — heartbeat msw handler

**Frontend tests:**
- `frontend/src/hooks/__tests__/useHeartbeat.test.tsx` — NEW. fake timers, asserts heartbeat fires
- `frontend/src/components/__tests__/EmptyAppState.test.tsx` — NEW. renders message + CTA
- `frontend/src/pages/__tests__/DashboardPage.test.tsx` — NEW (if not exists). empty categories → empty state
- `frontend/src/components/dashboard/__tests__/CategoryDonut.test.tsx` — NEW. legend includes % text

**Launcher:**
- `scripts/start.ps1` — add `/api/health` probe before port-busy check; if ours, just open browser

**Packaging (new):**
- `scripts/package.ps1` — NEW. End-to-end build (frontend → staging → Python embed → deps → installer)
- `scripts/installer.iss` — NEW. Inno Setup script
- `scripts/portable/RUN.bat` — NEW. Friend's launcher (sets FA_DB_PATH, calls embedded python)
- `scripts/portable/STOP.bat` — NEW. Friend's stop script
- `scripts/portable/README.txt` — NEW. Friend-facing docs (SmartScreen workaround, basic usage)

**Repo docs (new):**
- `.github/release-notes-template.md` — NEW. Template for GitHub release descriptions

---

### Task 1: FA_DB_PATH config + database.py wiring

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/database.py:11-14`
- Test: `backend/tests/test_config.py` (NEW)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_config.py`:

```python
from pathlib import Path

from app.config import Settings


def test_resolved_url_defaults_to_database_url(tmp_path, monkeypatch):
    monkeypatch.delenv("FA_DB_PATH", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    s = Settings(_env_file=None)
    assert s.resolved_database_url() == "sqlite:///./financial.db"


def test_resolved_url_uses_fa_db_path_when_set(tmp_path, monkeypatch):
    target = tmp_path / "data" / "fa.db"
    monkeypatch.setenv("FA_DB_PATH", str(target))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    s = Settings(_env_file=None)
    url = s.resolved_database_url()
    assert url == f"sqlite:///{target}"
    # parent directory created on resolve
    assert target.parent.is_dir()


def test_resolved_url_fa_db_path_overrides_database_url(tmp_path, monkeypatch):
    target = tmp_path / "fa.db"
    monkeypatch.setenv("FA_DB_PATH", str(target))
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./should-not-be-used.db")
    s = Settings(_env_file=None)
    assert s.resolved_database_url() == f"sqlite:///{target}"
```

- [ ] **Step 2: Run the test and verify it fails**

```
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_config.py -v
```

Expected: `AttributeError: 'Settings' object has no attribute 'resolved_database_url'`

- [ ] **Step 3: Update `app/config.py`**

Replace the file contents with:

```python
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./financial.db"
    fa_db_path: str | None = None

    def resolved_database_url(self) -> str:
        if self.fa_db_path:
            p = Path(self.fa_db_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{p.as_posix()}"
        return self.database_url


settings = Settings()
```

- [ ] **Step 4: Update `app/database.py`**

Change line 12 from:

```python
engine = create_engine(
    settings.database_url,
```

to:

```python
engine = create_engine(
    settings.resolved_database_url(),
```

And change line 16 from:

```python
if settings.database_url.startswith("sqlite"):
```

to:

```python
if settings.resolved_database_url().startswith("sqlite"):
```

- [ ] **Step 5: Run tests, verify pass + nothing else broke**

```
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_config.py -v
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: 3 new tests pass, total stays at 99+3=102 passing.

- [ ] **Step 6: Commit**

```
git add backend/app/config.py backend/app/database.py backend/tests/test_config.py
git commit -m "feat(backend): FA_DB_PATH env var to override DB location

Lets the portable build target %APPDATA% without changing wife setup —
default behaviour (no env var set) keeps DB at backend/financial.db.
Parent directory auto-created on resolve so launcher doesn't need to mkdir.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: Heartbeat endpoint

**Files:**
- Create: `backend/app/routers/heartbeat.py`
- Modify: `backend/app/main.py:12,43-49` (imports + router wiring)
- Test: `backend/tests/test_heartbeat.py` (NEW)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_heartbeat.py`:

```python
def test_heartbeat_returns_ok(client):
    response = client.post("/api/heartbeat")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_heartbeat_does_not_require_auth(client):
    # No auth override on this route — the dependency override on get_current_user_id
    # in conftest is harmless because heartbeat doesn't depend on it.
    response = client.post("/api/heartbeat")
    assert response.status_code == 200
```

- [ ] **Step 2: Run test, verify it fails**

```
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_heartbeat.py -v
```

Expected: 404 Not Found on both tests (route doesn't exist yet).

- [ ] **Step 3: Create `backend/app/routers/heartbeat.py`**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["heartbeat"])


@router.post("/heartbeat")
def heartbeat() -> dict[str, bool]:
    return {"ok": True}
```

- [ ] **Step 4: Wire it in `backend/app/main.py`**

Find this line (around line 12):

```python
from app.routers import budgets, categories, csv_import, export, health, import_presets, transactions
```

Change to:

```python
from app.routers import budgets, categories, csv_import, export, health, heartbeat, import_presets, transactions
```

Find the block of `app.include_router(...)` calls (around line 43-49) and add:

```python
app.include_router(heartbeat.router)
```

immediately after the `app.include_router(health.router)` line.

- [ ] **Step 5: Run tests**

```
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_heartbeat.py -v
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: 2 new tests pass, total 104.

- [ ] **Step 6: Commit**

```
git add backend/app/routers/heartbeat.py backend/app/main.py backend/tests/test_heartbeat.py
git commit -m "feat(backend): POST /api/heartbeat endpoint

Will be called by the frontend every 5 min while a tab is open so the
idle watchdog (next task) knows the app is still in use.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: Last-activity middleware + idle watchdog

**Files:**
- Create: `backend/app/idle.py`
- Modify: `backend/app/main.py` (lifespan + middleware)
- Test: `backend/tests/test_idle_watchdog.py` (NEW)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_idle_watchdog.py`:

```python
import asyncio
import time
from unittest.mock import patch

import pytest

from app import idle


@pytest.fixture(autouse=True)
def reset_idle_state():
    idle._last_activity = time.monotonic()
    yield


def test_record_activity_updates_timestamp():
    before = idle._last_activity
    time.sleep(0.01)
    idle.record_activity()
    assert idle._last_activity > before


def test_seconds_since_activity_increases_with_time():
    idle.record_activity()
    time.sleep(0.05)
    elapsed = idle.seconds_since_activity()
    assert elapsed >= 0.05


@pytest.mark.asyncio
async def test_watchdog_does_not_shutdown_when_active():
    idle.record_activity()
    with patch("app.idle._trigger_shutdown") as mock_shutdown:
        # Loop with a 50 ms check interval and a 1 s idle threshold.
        # Run for 150 ms — well under threshold; record activity midway.
        task = asyncio.create_task(
            idle._watchdog_loop(check_interval=0.05, idle_threshold=1.0)
        )
        await asyncio.sleep(0.07)
        idle.record_activity()
        await asyncio.sleep(0.07)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        mock_shutdown.assert_not_called()


@pytest.mark.asyncio
async def test_watchdog_triggers_shutdown_after_threshold():
    # Force the idle timestamp into the past.
    idle._last_activity = time.monotonic() - 100.0
    with patch("app.idle._trigger_shutdown") as mock_shutdown:
        task = asyncio.create_task(
            idle._watchdog_loop(check_interval=0.05, idle_threshold=1.0)
        )
        # Watchdog should fire on first or second tick.
        await asyncio.sleep(0.15)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert mock_shutdown.called
```

Also add `pytest-asyncio` plumbing if not already in `pyproject.toml`/`pytest.ini`. Check first:

```
cd backend
.\.venv\Scripts\python.exe -m pip show pytest-asyncio
```

If not installed:

```
.\.venv\Scripts\python.exe -m pip install pytest-asyncio
```

And add to `backend/requirements.txt` after the line containing `pytest`:

```
pytest-asyncio==0.24.0
```

Create or modify `backend/pytest.ini` to add:

```ini
[pytest]
asyncio_mode = auto
```

(If `pytest.ini` exists already, just add the asyncio_mode line under the existing `[pytest]` section.)

- [ ] **Step 2: Run test, verify it fails**

```
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_idle_watchdog.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.idle'` (and/or import errors).

- [ ] **Step 3: Create `backend/app/idle.py`**

```python
"""Idle-shutdown watchdog.

The frontend posts /api/heartbeat every 5 minutes while a tab is open.
A middleware updates ``_last_activity`` on every HTTP request (heartbeat or
otherwise). A background asyncio task started from the FastAPI lifespan
checks every minute whether more than ``IDLE_THRESHOLD_SECONDS`` have passed
since the last activity; if so, it raises SIGINT in this process. Uvicorn
handles the signal by closing connections gracefully and exiting.
"""

from __future__ import annotations

import asyncio
import os
import signal
import time

IDLE_THRESHOLD_SECONDS = 60 * 60
CHECK_INTERVAL_SECONDS = 60

_last_activity: float = time.monotonic()


def record_activity() -> None:
    global _last_activity
    _last_activity = time.monotonic()


def seconds_since_activity() -> float:
    return time.monotonic() - _last_activity


def _trigger_shutdown() -> None:
    # SIGINT triggers uvicorn's graceful shutdown path on both POSIX and
    # Windows (Python 3.x supports raising signals in the current process
    # on Windows since 3.8).
    os.kill(os.getpid(), signal.SIGINT)


async def _watchdog_loop(
    check_interval: float = CHECK_INTERVAL_SECONDS,
    idle_threshold: float = IDLE_THRESHOLD_SECONDS,
) -> None:
    while True:
        await asyncio.sleep(check_interval)
        if seconds_since_activity() > idle_threshold:
            _trigger_shutdown()
            return


def start_watchdog() -> asyncio.Task:
    return asyncio.create_task(_watchdog_loop())
```

- [ ] **Step 4: Add middleware + watchdog to `backend/app/main.py`**

Find the imports block at the top and add (alongside the other `app.*` imports):

```python
from app import idle
```

After `app = FastAPI(...)` and the existing `add_middleware` calls, add:

```python
@app.middleware("http")
async def _track_activity(request, call_next):
    idle.record_activity()
    return await call_next(request)
```

Modify the `lifespan` function to start the watchdog. Replace the existing lifespan:

```python
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
```

with:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    run_migrations(engine)
    db = SessionLocal()
    try:
        recurring_service.run_due_schedules(db, today=date.today())
    finally:
        db.close()
    watchdog_task = idle.start_watchdog()
    try:
        yield
    finally:
        watchdog_task.cancel()
        try:
            await watchdog_task
        except asyncio.CancelledError:
            pass
```

Also add at the top of `main.py` (with the other stdlib imports):

```python
import asyncio
```

- [ ] **Step 5: Run all backend tests**

```
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: 104 + 4 = 108 passing.

- [ ] **Step 6: Commit**

```
git add backend/app/idle.py backend/app/main.py backend/tests/test_idle_watchdog.py backend/requirements.txt backend/pytest.ini
git commit -m "feat(backend): idle-shutdown watchdog after 60 min inactivity

Middleware bumps last-activity on every request (including the frontend
heartbeat). A background task in the lifespan checks every 60 s and raises
SIGINT once the threshold is crossed — uvicorn then closes connections
gracefully and exits, freeing port 8000. Next start.bat launches fresh.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: Frontend useHeartbeat hook

**Files:**
- Create: `frontend/src/api/heartbeat.ts`
- Create: `frontend/src/hooks/useHeartbeat.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/tests/handlers.ts`
- Test: `frontend/src/hooks/__tests__/useHeartbeat.test.tsx` (NEW)

- [ ] **Step 1: Add msw handler**

In `frontend/src/tests/handlers.ts`, add to the `handlers` array (next to the other `http.post` handlers):

```typescript
http.post("/api/heartbeat", () => HttpResponse.json({ ok: true })),
```

- [ ] **Step 2: Write the failing test**

Create `frontend/src/hooks/__tests__/useHeartbeat.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { server } from "../../tests/server";
import { http, HttpResponse } from "msw";
import { useHeartbeat } from "../useHeartbeat";

describe("useHeartbeat", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("posts /api/heartbeat once per interval while mounted", async () => {
    const calls: number = await new Promise((resolve) => {
      let n = 0;
      server.use(
        http.post("/api/heartbeat", () => {
          n += 1;
          return HttpResponse.json({ ok: true });
        }),
      );
      renderHook(() => useHeartbeat(1000));
      // first immediate tick + two intervals
      Promise.resolve().then(async () => {
        await vi.advanceTimersByTimeAsync(0);
        await vi.advanceTimersByTimeAsync(1000);
        await vi.advanceTimersByTimeAsync(1000);
        resolve(n);
      });
    });
    expect(calls).toBeGreaterThanOrEqual(2);
  });

  it("does not post after unmount", async () => {
    let n = 0;
    server.use(
      http.post("/api/heartbeat", () => {
        n += 1;
        return HttpResponse.json({ ok: true });
      }),
    );
    const { unmount } = renderHook(() => useHeartbeat(1000));
    await vi.advanceTimersByTimeAsync(0);
    const afterMount = n;
    unmount();
    await vi.advanceTimersByTimeAsync(5000);
    expect(n).toBe(afterMount);
  });
});
```

- [ ] **Step 3: Run test, verify it fails**

```
cd frontend
npm test -- --run useHeartbeat
```

Expected: `Cannot find module '../useHeartbeat'`.

- [ ] **Step 4: Create `frontend/src/api/heartbeat.ts`**

```typescript
import { apiFetch } from "./apiFetch";

export async function postHeartbeat(): Promise<void> {
  await apiFetch("/api/heartbeat", { method: "POST" });
}
```

(If `apiFetch` lives at a different path, follow the import pattern from other `frontend/src/api/*.ts` files — they all import `apiFetch` similarly.)

- [ ] **Step 5: Create `frontend/src/hooks/useHeartbeat.ts`**

```typescript
import { useEffect } from "react";
import { postHeartbeat } from "@/api/heartbeat";

const DEFAULT_INTERVAL_MS = 5 * 60 * 1000;

/**
 * Sends a POST /api/heartbeat at startup and every `intervalMs` thereafter
 * while the component is mounted. The backend uses this to know a tab is
 * still open so the idle watchdog doesn't shut it down.
 */
export function useHeartbeat(intervalMs: number = DEFAULT_INTERVAL_MS) {
  useEffect(() => {
    // Fire-and-forget — heartbeat failures are not user-visible.
    void postHeartbeat();
    const handle = setInterval(() => {
      void postHeartbeat();
    }, intervalMs);
    return () => clearInterval(handle);
  }, [intervalMs]);
}
```

- [ ] **Step 6: Wire `useHeartbeat()` into `App.tsx`**

Replace `frontend/src/App.tsx` with:

```typescript
import { RouterProvider } from "react-router-dom";
import { router } from "./routes";
import { useHeartbeat } from "./hooks/useHeartbeat";

export default function App() {
  useHeartbeat();
  return <RouterProvider router={router} />;
}
```

- [ ] **Step 7: Run frontend tests**

```
cd frontend
npm test -- --run
```

Expected: 52 + 2 = 54 passing.

- [ ] **Step 8: Commit**

```
git add frontend/src/api/heartbeat.ts frontend/src/hooks/useHeartbeat.ts frontend/src/App.tsx frontend/src/tests/handlers.ts frontend/src/hooks/__tests__/useHeartbeat.test.tsx
git commit -m "feat(frontend): post /api/heartbeat every 5 min while tab is open

Keeps the backend idle watchdog from shutting down while a tab is active.
First heartbeat fires on mount; thereafter every 5 minutes. Cleared on
unmount.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: EmptyAppState component + Dashboard empty state

**Files:**
- Create: `frontend/src/components/EmptyAppState.tsx`
- Modify: `frontend/src/pages/DashboardPage.tsx`
- Test: `frontend/src/components/__tests__/EmptyAppState.test.tsx` (NEW)
- Test: `frontend/src/pages/__tests__/DashboardPage.test.tsx` (NEW or modify)

- [ ] **Step 1: Write the EmptyAppState test**

Create `frontend/src/components/__tests__/EmptyAppState.test.tsx`:

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { EmptyAppState } from "../EmptyAppState";

function renderWithRouter(ui: React.ReactNode) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("EmptyAppState", () => {
  it("shows the welcome message and a CTA link to /categories", () => {
    renderWithRouter(<EmptyAppState />);
    expect(screen.getByText(/welcome to financial assistant/i)).toBeInTheDocument();
    const cta = screen.getByRole("link", { name: /create your first category/i });
    expect(cta).toHaveAttribute("href", "/categories");
  });
});
```

- [ ] **Step 2: Run test, verify it fails**

```
cd frontend
npm test -- --run EmptyAppState
```

Expected: `Cannot find module '../EmptyAppState'`.

- [ ] **Step 3: Create `frontend/src/components/EmptyAppState.tsx`**

```typescript
import { Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function EmptyAppState() {
  return (
    <Card>
      <CardContent className="py-12 flex flex-col items-center text-center gap-4">
        <h3 className="text-xl font-semibold">Welcome to Financial Assistant</h3>
        <p className="text-muted-foreground max-w-md">
          Start by creating a few categories — income, expense, and savings buckets you
          want to track. Once you have at least one, you can add transactions and set budgets.
        </p>
        <Button asChild>
          <Link to="/categories">Create your first category</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Run EmptyAppState test, verify pass**

```
cd frontend
npm test -- --run EmptyAppState
```

Expected: 1 test passes.

- [ ] **Step 5: Write the DashboardPage empty-state test**

Check first whether `frontend/src/pages/__tests__/DashboardPage.test.tsx` exists. If not, create it:

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import DashboardPage from "../DashboardPage";
import { testState } from "@/tests/handlers";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/?month=2026-05"]}>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    testState.categories = [];
    testState.transactions = [];
    testState.budgets = [];
  });

  it("shows EmptyAppState when there are no categories", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/welcome to financial assistant/i)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 6: Run, verify it fails**

```
cd frontend
npm test -- --run DashboardPage
```

Expected: empty-state text not found (the page renders the normal layout instead).

- [ ] **Step 7: Modify `frontend/src/pages/DashboardPage.tsx`**

Replace the file contents with:

```typescript
import { KpiRow } from "@/components/dashboard/KpiRow";
import { BudgetWidget } from "@/components/dashboard/BudgetWidget";
import { RecentTransactions } from "@/components/dashboard/RecentTransactions";
import { CategoryDonut } from "@/components/dashboard/CategoryDonut";
import { MonthlyTrendBar } from "@/components/dashboard/MonthlyTrendBar";
import { SavingsGoalsRow } from "@/components/dashboard/SavingsGoalsRow";
import { EmptyAppState } from "@/components/EmptyAppState";
import { useUrlMonth } from "@/hooks/useUrlMonth";
import { useCategories } from "@/hooks/queries/useCategories";
import { monthLabel } from "@/lib/date";

export default function DashboardPage() {
  const { month } = useUrlMonth();
  const { data: cats, isLoading } = useCategories();

  if (!isLoading && (cats?.length ?? 0) === 0) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold">Dashboard</h2>
        <EmptyAppState />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Dashboard — {monthLabel(month)}</h2>
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

- [ ] **Step 8: Run tests, verify pass**

```
cd frontend
npm test -- --run
```

Expected: 54 + 2 = 56 passing.

- [ ] **Step 9: Commit**

```
git add frontend/src/components/EmptyAppState.tsx frontend/src/components/__tests__/EmptyAppState.test.tsx frontend/src/pages/DashboardPage.tsx frontend/src/pages/__tests__/DashboardPage.test.tsx
git commit -m "feat(frontend): empty-state guidance on Dashboard when no categories

First-run UX: instead of a dashboard full of zero-value cards, show a
Welcome card with a CTA pointing at /categories. EmptyAppState is reused
by the other top-level pages in the next tasks.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: Transactions page empty state

**Files:**
- Modify: `frontend/src/pages/TransactionsPage.tsx`
- Test: `frontend/src/pages/__tests__/TransactionsPage.test.tsx` (NEW or modify)

- [ ] **Step 1: Write the failing test**

Check if `frontend/src/pages/__tests__/TransactionsPage.test.tsx` exists. If not, create it with:

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import TransactionsPage from "../TransactionsPage";
import { testState } from "@/tests/handlers";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/transactions?month=2026-05"]}>
        <TransactionsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TransactionsPage empty state", () => {
  beforeEach(() => {
    testState.categories = [];
    testState.transactions = [];
  });

  it("shows EmptyAppState when there are no categories", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/welcome to financial assistant/i)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Run, verify it fails**

```
cd frontend
npm test -- --run TransactionsPage
```

Expected: text not found.

- [ ] **Step 3: Update `frontend/src/pages/TransactionsPage.tsx`**

Find the existing component and wrap the empty-categories case. Replace the file body with:

```typescript
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { TransactionsTable } from "@/components/transactions/TransactionsTable";
import { EmptyAppState } from "@/components/EmptyAppState";
import { useUrlMonth } from "@/hooks/useUrlMonth";
import { useCategories } from "@/hooks/queries/useCategories";
import { useSearchParams } from "react-router-dom";
import { monthLabel } from "@/lib/date";

export default function TransactionsPage() {
  const { month } = useUrlMonth();
  const { data: cats, isLoading } = useCategories();
  const [params, setParams] = useSearchParams();
  const catParam = params.get("category_id");
  const categoryId = catParam ? Number(catParam) : undefined;

  function onCategoryChange(next: string) {
    const np = new URLSearchParams(params);
    if (next === "all") np.delete("category_id");
    else np.set("category_id", next);
    setParams(np);
  }

  if (!isLoading && (cats?.length ?? 0) === 0) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold">Transactions</h2>
        <EmptyAppState />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">
          Transactions — {monthLabel(month)}
        </h2>
        <div className="flex items-end gap-2">
          <div>
            <Label htmlFor="tx-cat-filter" className="text-xs text-muted-foreground">
              Category
            </Label>
            <Select
              value={categoryId ? String(categoryId) : "all"}
              onValueChange={onCategoryChange}
            >
              <SelectTrigger id="tx-cat-filter" className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {(cats ?? []).map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
      <TransactionsTable month={month} categoryId={categoryId} />
    </div>
  );
}
```

- [ ] **Step 4: Run, verify pass**

```
cd frontend
npm test -- --run
```

Expected: 56 + 1 = 57 passing.

- [ ] **Step 5: Commit**

```
git add frontend/src/pages/TransactionsPage.tsx frontend/src/pages/__tests__/TransactionsPage.test.tsx
git commit -m "feat(frontend): empty-state guidance on Transactions page

When no categories exist, Transactions can't even be added (category is
required), so show the same Welcome CTA pointing at /categories.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 7: Budgets page empty state

**Files:**
- Modify: `frontend/src/pages/BudgetsPage.tsx`
- Test: `frontend/src/pages/__tests__/BudgetsPage.test.tsx` (NEW or modify)

- [ ] **Step 1: Read `frontend/src/pages/BudgetsPage.tsx`**

First read the file to see its structure — the modification follows the same pattern as Transactions but the imports/layout may differ.

- [ ] **Step 2: Write the failing test**

Adapt the Transactions test pattern. Create or extend `frontend/src/pages/__tests__/BudgetsPage.test.tsx`:

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import BudgetsPage from "../BudgetsPage";
import { testState } from "@/tests/handlers";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/budgets?month=2026-05"]}>
        <BudgetsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("BudgetsPage empty state", () => {
  beforeEach(() => {
    testState.categories = [];
    testState.budgets = [];
    testState.transactions = [];
  });

  it("shows EmptyAppState when there are no categories", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/welcome to financial assistant/i)).toBeInTheDocument();
    });
  });
});
```

If `BudgetsPage` is not the default export, adjust the import.

- [ ] **Step 3: Run, verify it fails**

```
cd frontend
npm test -- --run BudgetsPage
```

- [ ] **Step 4: Update `frontend/src/pages/BudgetsPage.tsx`**

Add at the top of the component (immediately after fetching categories):

```typescript
import { EmptyAppState } from "@/components/EmptyAppState";
// ... (other existing imports)

// Inside the component, after const { data: cats, isLoading } = useCategories();:
if (!isLoading && (cats?.length ?? 0) === 0) {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Budgets</h2>
      <EmptyAppState />
    </div>
  );
}
```

If the existing component doesn't already fetch categories, add `const { data: cats, isLoading } = useCategories();` at the top of the component body.

- [ ] **Step 5: Run, verify pass**

```
cd frontend
npm test -- --run
```

Expected: 57 + 1 = 58 passing.

- [ ] **Step 6: Commit**

```
git add frontend/src/pages/BudgetsPage.tsx frontend/src/pages/__tests__/BudgetsPage.test.tsx
git commit -m "feat(frontend): empty-state guidance on Budgets page

Same Welcome CTA pattern as Dashboard and Transactions — Budgets require
a category, so when there are none we point the user to /categories first.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 8: Donut chart legend with % always visible

**Files:**
- Modify: `frontend/src/components/dashboard/CategoryDonut.tsx`
- Test: `frontend/src/components/dashboard/__tests__/CategoryDonut.test.tsx` (NEW)

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/dashboard/__tests__/CategoryDonut.test.tsx`:

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CategoryDonut } from "../CategoryDonut";
import { testState } from "@/tests/handlers";

function renderDonut() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CategoryDonut month="2026-05" />
    </QueryClientProvider>,
  );
}

describe("CategoryDonut legend", () => {
  beforeEach(() => {
    testState.categories = [
      { id: 1, name: "Groceries", kind: "expense", target_amount: null, target_date: null, created_at: "2026-05-01T00:00:00" },
      { id: 2, name: "Eating-out", kind: "expense", target_amount: null, target_date: null, created_at: "2026-05-01T00:00:00" },
    ];
    testState.transactions = [
      { id: 1, user_id: 1, amount: "75", description: "", date: "2026-05-10", category_id: 1, created_at: "" },
      { id: 2, user_id: 1, amount: "25", description: "", date: "2026-05-11", category_id: 2, created_at: "" },
    ];
  });

  it("legend shows category name plus percent for each slice", async () => {
    renderDonut();
    await waitFor(() => {
      expect(screen.getByText(/Groceries.*75%/)).toBeInTheDocument();
      expect(screen.getByText(/Eating-out.*25%/)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Run, verify it fails**

```
cd frontend
npm test -- --run CategoryDonut
```

Expected: regex `Groceries.*75%` not found — the current legend only shows the name.

- [ ] **Step 3: Modify `frontend/src/components/dashboard/CategoryDonut.tsx`**

Replace the `<ChartLegend ... />` JSX inside the component with a custom legend renderer. Find this line (around line 103):

```typescript
<ChartLegend
  content={<ChartLegendContent nameKey="category" />}
/>
```

Replace with:

```typescript
<ChartLegend
  content={() => (
    <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 pt-3 text-xs">
      {slices.map((s) => {
        const pct = total > 0 ? (s.amount / total) * 100 : 0;
        return (
          <div key={s.category} className="flex items-center gap-1.5">
            <span
              className="inline-block h-2 w-2 rounded-[2px]"
              style={{ backgroundColor: s.fill }}
              aria-hidden
            />
            <span>{s.category}</span>
            <span className="text-muted-foreground">({pct.toFixed(0)}%)</span>
          </div>
        );
      })}
    </div>
  )}
/>
```

Remove the now-unused import `ChartLegendContent` from the imports block (around line 5-8) if it's not used elsewhere in the file.

- [ ] **Step 4: Run, verify pass**

```
cd frontend
npm test -- --run CategoryDonut
```

Expected: 1 test passes.

Then run all tests:

```
npm test -- --run
```

Expected: 58 + 1 = 59 passing.

- [ ] **Step 5: Commit**

```
git add frontend/src/components/dashboard/CategoryDonut.tsx frontend/src/components/dashboard/__tests__/CategoryDonut.test.tsx
git commit -m "feat(frontend): donut chart legend shows percent inline

Previously percent was only visible on hover (in the tooltip). Now each
legend item shows '<Category> (NN%)' so the breakdown is readable at a
glance.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 9: Launcher port-reuse via /api/health probe

**Files:**
- Modify: `scripts/start.ps1` (the `# Pre-check: is port 8000 free?` block, currently ~line 34-38)

- [ ] **Step 1: Read the current state of `scripts/start.ps1`**

Confirm the block hasn't changed since the cache-buster fix.

- [ ] **Step 2: Modify the pre-check block**

Replace this block (the `# Pre-check: is port 8000 free?` section):

```powershell
# Pre-check: is port 8000 free? Filter to State=Listen — leftover client sockets
# from a previous run sit in FinWait2/TimeWait for ~30s and would otherwise make
# this look busy when no one is actually listening.
$portBusy = $null -ne (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
if ($portBusy) {
    Fail "Port 8000 is already in use. The app may already be running, or another program is holding the port. Close it from Task Manager and try again."
}
```

with:

```powershell
# Pre-check: is port 8000 free? Filter to State=Listen — leftover client sockets
# from a previous run sit in FinWait2/TimeWait for ~30s and would otherwise make
# this look busy when no one is actually listening.
$portBusy = $null -ne (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
if ($portBusy) {
    # If it's our own backend already running, just open a browser tab and exit.
    # Identification: /api/health responds 200 with {"status":"ok"} only in our app.
    $oursAlready = $false
    try {
        $r = Invoke-WebRequest "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200 -and $r.Content -match '"status"\s*:\s*"ok"') {
            $oursAlready = $true
        }
    } catch { }

    if ($oursAlready) {
        $launchToken = [DateTimeOffset]::Now.ToUnixTimeSeconds()
        Start-Process "http://localhost:8000/?v=$launchToken"
        exit 0
    }

    Fail "Port 8000 is already in use by another program. Close it from Task Manager and try again."
}
```

- [ ] **Step 3: Parse-check**

```powershell
$null = [scriptblock]::Create((Get-Content "D:\Projects\Claude\Financial_Assistant\scripts\start.ps1" -Raw))
Write-Host "start.ps1: parse OK"
```

- [ ] **Step 4: Manual smoke test**

1. Start the app via `D:\Projects\Claude\Financial_Assistant\scripts\start.bat`. Confirm browser opens, app loads.
2. Without stopping, run `start.bat` again. Confirm a second browser tab opens to `http://localhost:8000/?v=...`, no MessageBox, no error log lines added.
3. Stop via `scripts\stop.bat`.
4. Run `python -m http.server 8000` from any directory (or any other process holding port 8000). Run `start.bat`. Confirm the old "Port 8000 is already in use by another program" MessageBox appears (different process means health probe fails).
5. Stop the test process.

- [ ] **Step 5: Commit**

```
git add scripts/start.ps1
git commit -m "feat(launcher): reuse running instance instead of failing on port-busy

When start.bat is run while the app is already serving on :8000, probe
/api/health to confirm it's our backend; if so, just open a new browser
tab and exit cleanly. Only error out if the port is held by something
else.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 10: Portable folder templates (RUN.bat, STOP.bat, README.txt)

**Files:**
- Create: `scripts/portable/RUN.bat`
- Create: `scripts/portable/STOP.bat`
- Create: `scripts/portable/README.txt`

These are templates copied verbatim into the installer's payload. The end-user only ever sees these three files plus the (hidden) `python/`, `backend/`, `frontend/`, `app-scripts/` folders.

- [ ] **Step 1: Create `scripts/portable/RUN.bat`**

```batch
@echo off
REM Financial Assistant launcher (portable build).
REM Sets FA_DB_PATH to %APPDATA%\FinancialAssistant\ so the database survives reinstalls.

setlocal

set "INSTALL_DIR=%~dp0"
set "FA_DB_PATH=%APPDATA%\FinancialAssistant\financial.db"

REM Ensure the data directory exists.
if not exist "%APPDATA%\FinancialAssistant" mkdir "%APPDATA%\FinancialAssistant"

powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%INSTALL_DIR%app-scripts\start.ps1"
```

- [ ] **Step 2: Create `scripts/portable/STOP.bat`**

```batch
@echo off
REM Stops Financial Assistant (portable build).
setlocal
set "INSTALL_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%INSTALL_DIR%app-scripts\stop.ps1"
```

- [ ] **Step 3: Create `scripts/portable/README.txt`**

```
FINANCIAL ASSISTANT — Portable Build
====================================

Indítás
-------
  Dupla katt: RUN.bat   (vagy a Start menü "Financial Assistant" ikonjára)
  Egy böngészőablak nyílik a http://localhost:8000 címmel.
  Az app 1 órányi tétlenség után automatikusan leáll — a következő indítás
  pár másodperc alatt újra elindítja.

Leállítás (ha nem akarod megvárni az auto-leállást)
---------------------------------------------------
  Dupla katt: STOP.bat   (vagy Start menü "Stop Financial Assistant")

Hova kerül az adatod
--------------------
  %APPDATA%\FinancialAssistant\financial.db
  (Az újratelepítés vagy frissítés nem törli — biztonságos backup-olni
  innen, ha akarsz.)

Ha SmartScreen figyelmeztet az installer-re ("Windows protected your PC")
------------------------------------------------------------------------
  Az installer nincs aláírva (egy magánfejlesztő csomagja).
  Kattints: "More info" → "Run anyway".
  Ez egyszeri lépés.

Probléma esetén
---------------
  A naplófájlok itt találhatók:
    <install_dir>\app-scripts\uvicorn-stderr.log
    <install_dir>\app-scripts\start-error.log
    <install_dir>\app-scripts\stop.log
  Küldd el ezeket annak akitől a programot kaptad.

Forrás
------
  https://github.com/Donuttouchme/Financial_Assistant
```

- [ ] **Step 4: Commit**

```
git add scripts/portable/RUN.bat scripts/portable/STOP.bat scripts/portable/README.txt
git commit -m "feat(packaging): friend-facing launcher templates for portable build

Three files the recipient sees: RUN.bat (sets FA_DB_PATH, calls hidden
PowerShell), STOP.bat (mirror for shutdown), and a Hungarian README.txt
explaining first-run, SmartScreen workaround, and where the DB lives.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 11: package.ps1 — frontend build + backend staging

**Files:**
- Create: `scripts/package.ps1`

The build script grows over the next three tasks. This task implements:
1. Clean output directory
2. Run frontend build
3. Stage backend + frontend/dist into `dist/portable-staging/`

- [ ] **Step 1: Create `scripts/package.ps1`**

```powershell
# Builds the portable distribution.
# Output: dist/Financial-Assistant-Setup-v<version>.exe
#
# Usage: .\scripts\package.ps1 -Version "1.0"
#
# Requires:
#   - Node.js (already installed for frontend dev)
#   - Inno Setup 6 (ISCC.exe at $env:LOCALAPPDATA\Programs\Inno Setup 6\)
#   - Internet (downloads Python 3.14 embed on first run)

param(
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$staging = Join-Path $root "dist\portable-staging"
$out = Join-Path $root "dist"

Write-Host "=== Financial Assistant portable build v$Version ==="
Write-Host "root:    $root"
Write-Host "staging: $staging"
Write-Host ""

# 1) Clean staging
if (Test-Path $staging) {
    Write-Host "[1/N] Cleaning staging..."
    Remove-Item -Recurse -Force $staging
}
New-Item -ItemType Directory -Force -Path $staging | Out-Null

# 2) Frontend build
Write-Host "[2/N] Building frontend..."
Push-Location (Join-Path $root "frontend")
try {
    & npm install 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
    & npm run build 2>&1 | Tee-Object -Variable buildOut
    if ($LASTEXITCODE -ne 0) {
        $buildOut | Write-Host
        throw "npm run build failed"
    }
} finally {
    Pop-Location
}

# 3) Stage frontend dist
Write-Host "[3/N] Staging frontend/dist..."
New-Item -ItemType Directory -Force -Path (Join-Path $staging "frontend") | Out-Null
Copy-Item -Recurse -Force (Join-Path $root "frontend\dist") (Join-Path $staging "frontend\dist")

# 4) Stage backend code (no venv, no DB, no caches)
Write-Host "[4/N] Staging backend code..."
$backendStage = Join-Path $staging "backend"
New-Item -ItemType Directory -Force -Path $backendStage | Out-Null
# Copy everything under backend/, then prune.
Copy-Item -Recurse -Force (Join-Path $root "backend\*") $backendStage -Exclude @(".venv", "financial.db", "financial.db.backup-*", "__pycache__", ".pytest_cache")
# Recursively delete __pycache__ that survived the top-level exclude.
Get-ChildItem -Recurse -Directory -Force -Path $backendStage -Filter "__pycache__" | Remove-Item -Recurse -Force

# 5) Stage app-scripts (start.ps1 + stop.ps1 only — no package.ps1 or build.bat)
Write-Host "[5/N] Staging launcher scripts..."
$appScripts = Join-Path $staging "app-scripts"
New-Item -ItemType Directory -Force -Path $appScripts | Out-Null
Copy-Item (Join-Path $root "scripts\start.ps1") $appScripts
Copy-Item (Join-Path $root "scripts\stop.ps1") $appScripts

# 6) Stage friend-facing root templates (RUN.bat, STOP.bat, README.txt)
Write-Host "[6/N] Staging RUN.bat, STOP.bat, README.txt..."
Copy-Item (Join-Path $root "scripts\portable\RUN.bat") $staging
Copy-Item (Join-Path $root "scripts\portable\STOP.bat") $staging
Copy-Item (Join-Path $root "scripts\portable\README.txt") $staging

Write-Host ""
Write-Host "Stage complete: $staging"
Write-Host "Next steps (later tasks): download embedded Python, install deps, run Inno Setup."
```

- [ ] **Step 2: Run it once and verify staging layout**

```powershell
.\scripts\package.ps1 -Version "1.0-dev"
```

Then check:

```powershell
Get-ChildItem -Recurse "D:\Projects\Claude\Financial_Assistant\dist\portable-staging" -Depth 1
```

Expected: `backend/`, `frontend/dist/`, `app-scripts/`, `RUN.bat`, `STOP.bat`, `README.txt`. No `.venv`, no `financial.db`, no `__pycache__`.

- [ ] **Step 3: Add `dist/` to `.gitignore` if not already**

Check `D:\Projects\Claude\Financial_Assistant\.gitignore`. If `dist/` and `dist` aren't listed:

```
dist/
```

- [ ] **Step 4: Commit**

```
git add scripts/package.ps1 .gitignore
git commit -m "feat(packaging): package.ps1 stages frontend + backend for installer

Step 1 of the portable build: cleans dist/portable-staging, runs npm
build, copies backend code (minus venv/DB/caches), launcher scripts,
and the friend-facing templates. Next task installs an embedded Python
into this staging tree.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 12: package.ps1 — embedded Python + deps install

Extends `scripts/package.ps1` to download Python 3.14 embed, bootstrap pip, install backend dependencies into a `python/Lib/site-packages` folder.

**Files:**
- Modify: `scripts/package.ps1`

- [ ] **Step 1: Append the Python-embed staging logic to `scripts/package.ps1`**

Append the following at the end of the script (after the "Stage complete" Write-Host):

```powershell

# 7) Download Python 3.14 embedded distribution
$pythonEmbedUrl = "https://www.python.org/ftp/python/3.14.2/python-3.14.2-embed-amd64.zip"
$cacheDir = Join-Path $root "dist\cache"
$pythonZip = Join-Path $cacheDir "python-3.14.2-embed-amd64.zip"
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
if (-not (Test-Path $pythonZip)) {
    Write-Host "[7/N] Downloading Python 3.14 embeddable distribution..."
    Invoke-WebRequest -Uri $pythonEmbedUrl -OutFile $pythonZip
}
else {
    Write-Host "[7/N] Python embed zip cached at $pythonZip — skipping download."
}

# 8) Extract Python embed into staging/python
$pythonStage = Join-Path $staging "python"
Write-Host "[8/N] Extracting Python embed to $pythonStage..."
New-Item -ItemType Directory -Force -Path $pythonStage | Out-Null
Expand-Archive -Path $pythonZip -DestinationPath $pythonStage -Force

# 9) Enable site-packages by editing python314._pth
# The embed distribution ships with `import site` commented out, which
# disables site-packages loading. Uncomment it so pip-installed packages
# are importable.
$pthFile = Get-ChildItem -Path $pythonStage -Filter "python*._pth" | Select-Object -First 1
if (-not $pthFile) { throw "python._pth not found in $pythonStage" }
Write-Host "[9/N] Enabling site-packages in $($pthFile.Name)..."
$pthContent = Get-Content $pthFile.FullName
$pthContent = $pthContent | ForEach-Object { if ($_ -eq "#import site") { "import site" } else { $_ } }
Set-Content -Path $pthFile.FullName -Value $pthContent -Encoding ascii

# 10) Bootstrap pip via get-pip.py
$getPip = Join-Path $cacheDir "get-pip.py"
if (-not (Test-Path $getPip)) {
    Write-Host "[10/N] Downloading get-pip.py..."
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip
}
Write-Host "[10/N] Bootstrapping pip..."
$pythonExe = Join-Path $pythonStage "python.exe"
& $pythonExe $getPip --no-warn-script-location 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw "get-pip.py failed" }

# 11) Install backend deps into site-packages
Write-Host "[11/N] Installing backend dependencies..."
& $pythonExe -m pip install --no-warn-script-location -r (Join-Path $root "backend\requirements.txt") 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw "pip install -r requirements.txt failed" }

# 12) Smoke-test: can the embed Python import the backend?
Write-Host "[12/N] Smoke-test: importing backend..."
$env:PYTHONPATH = (Join-Path $staging "backend")
& $pythonExe -c "import app.main; print('app.main imports OK')"
$smokeRc = $LASTEXITCODE
$env:PYTHONPATH = $null
if ($smokeRc -ne 0) { throw "Embed-Python smoke test failed" }

Write-Host ""
Write-Host "=== Stage 12 complete. Python embed ready at $pythonStage ==="
```

- [ ] **Step 2: Update RUN.bat to call embed python**

Modify `scripts/portable/RUN.bat`. The portable build doesn't have an `uvicorn.exe` shim — replace the previous version with one that runs `python -m uvicorn`:

```batch
@echo off
REM Financial Assistant launcher (portable build).
REM Sets FA_DB_PATH to %APPDATA%\FinancialAssistant\ so the database survives reinstalls.

setlocal

set "INSTALL_DIR=%~dp0"
set "FA_DB_PATH=%APPDATA%\FinancialAssistant\financial.db"
set "PYTHON_EXE=%INSTALL_DIR%python\python.exe"

REM Ensure the data directory exists.
if not exist "%APPDATA%\FinancialAssistant" mkdir "%APPDATA%\FinancialAssistant"

powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%INSTALL_DIR%app-scripts\start.ps1" -PythonExe "%PYTHON_EXE%" -BackendDir "%INSTALL_DIR%backend"
```

- [ ] **Step 3: Update `app-scripts/start.ps1` to accept parameters when invoked portably**

Update `scripts/start.ps1` to accept optional `-PythonExe` and `-BackendDir` parameters. At the top of `start.ps1`, replace this:

```powershell
# Production-local launcher for Financial Assistant.
# ...
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
```

with:

```powershell
# Production-local launcher for Financial Assistant.
# ...
param(
    [string]$PythonExe = "",
    [string]$BackendDir = ""
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not $BackendDir) { $BackendDir = Join-Path $root "backend" }
Set-Location $root
```

Then find the block that resolves `$uvicornExe` (currently around line 55-58):

```powershell
$uvicornExe = Join-Path $root "backend\.venv\Scripts\uvicorn.exe"
if (-not (Test-Path $uvicornExe)) {
    Fail "uvicorn not found at $uvicornExe. ..."
}
```

Replace with:

```powershell
# When invoked from a portable build (RUN.bat passes -PythonExe), we run
# 'python -m uvicorn' via the embedded interpreter. The dev launcher uses
# the venv's uvicorn.exe shim as before.
if ($PythonExe) {
    if (-not (Test-Path $PythonExe)) {
        Fail "Embedded Python not found at $PythonExe. The portable install may be corrupt — try reinstalling."
    }
    $uvicornCmd = $PythonExe
    $uvicornArgs = @("-m", "uvicorn", "app.main:app", "--port", "8000")
}
else {
    $uvicornExe = Join-Path $root "backend\.venv\Scripts\uvicorn.exe"
    if (-not (Test-Path $uvicornExe)) {
        Fail "uvicorn not found at $uvicornExe. The backend virtualenv may be missing. Run: cd backend; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt"
    }
    $uvicornCmd = $uvicornExe
    $uvicornArgs = @("app.main:app", "--port", "8000")
}
```

Find the `Start-Process` call (currently around line 65-71):

```powershell
$uv = Start-Process -FilePath $uvicornExe `
    -ArgumentList "app.main:app","--port","8000" `
    -WorkingDirectory (Join-Path $root "backend") `
    -WindowStyle Hidden `
    -RedirectStandardOutput $uvOutLog `
    -RedirectStandardError $uvErrLog `
    -PassThru
```

Replace with:

```powershell
$uv = Start-Process -FilePath $uvicornCmd `
    -ArgumentList $uvicornArgs `
    -WorkingDirectory $BackendDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $uvOutLog `
    -RedirectStandardError $uvErrLog `
    -PassThru
```

- [ ] **Step 4: Run package.ps1 end-to-end and verify**

```powershell
.\scripts\package.ps1 -Version "1.0-dev"
```

Expected: completes through Step 12 with "Stage 12 complete. Python embed ready at ...". File listing of staging should now also contain `python/python.exe` and `python/Lib/site-packages/fastapi/`.

- [ ] **Step 5: Manual smoke test the staged backend**

In a fresh PowerShell window:

```powershell
$env:FA_DB_PATH = "$env:TEMP\fa-smoke-test\financial.db"
Set-Location "D:\Projects\Claude\Financial_Assistant\dist\portable-staging\backend"
..\python\python.exe -m uvicorn app.main:app --port 8001
```

Then in another PowerShell window:

```powershell
(Invoke-WebRequest "http://127.0.0.1:8001/api/health" -UseBasicParsing).Content
```

Expected: `{"status":"ok"}`. Stop with Ctrl+C in the first window. Check that the temp DB file was created.

- [ ] **Step 6: Commit**

```
git add scripts/package.ps1 scripts/portable/RUN.bat scripts/start.ps1
git commit -m "feat(packaging): embed Python 3.14 + deps into portable staging

Downloads python-3.14.2-embed-amd64.zip (cached after first download),
extracts, enables site-packages by uncommenting the ._pth line,
bootstraps pip, and installs backend/requirements.txt into the embed's
site-packages. The smoke step imports app.main to catch missing deps
before we ship.

start.ps1 now accepts -PythonExe / -BackendDir so RUN.bat in the portable
build can point it at the embedded interpreter; the dev path is
unchanged.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 13: Inno Setup script (installer.iss) + ISCC compile in package.ps1

**Files:**
- Create: `scripts/installer.iss`
- Modify: `scripts/package.ps1`

- [ ] **Step 1: Create `scripts/installer.iss`**

The script uses Inno Setup preprocessor for the version. The `AppId` GUID is fixed so future installers recognise prior installs as upgrades.

```pascal
; Financial Assistant Inno Setup script
; Run via:   ISCC.exe /DMyAppVersion=1.0 scripts/installer.iss

#define MyAppName "Financial Assistant"
#define MyAppPublisher "Donuttouchme"
#define MyAppURL "https://github.com/Donuttouchme/Financial_Assistant"
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif

[Setup]
; Fixed GUID — changing this would make a new release look like a separate app.
AppId={{8F4C9D2A-1B5E-4A6F-9C3D-7E8B2A1D5F0C}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\FinancialAssistant
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=
OutputDir=..\dist
OutputBaseFilename=Financial-Assistant-Setup-v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\RUN.bat
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\portable-staging\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\RUN.bat"; IconFilename: "{app}\frontend\dist\favicon.svg"; WorkingDir: "{app}"; Comment: "Open Financial Assistant in your browser"
Name: "{group}\Stop {#MyAppName}"; Filename: "{app}\STOP.bat"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\RUN.bat"; IconFilename: "{app}\frontend\dist\favicon.svg"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\RUN.bat"; Description: "Launch {#MyAppName} now"; Flags: postinstall nowait shellexec skipifsilent

[UninstallRun]
; Best-effort: stop the running backend before files get removed.
Filename: "{app}\STOP.bat"; RunOnceId: "StopFinancialAssistant"; Flags: skipifdoesntexist

[Code]
// Pre-install: if the app is running on :8000 and it's ours, ask user to stop.
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  Probe: TStringList;
begin
  Result := True;
  // We can't easily HTTP-probe from Inno Setup without external tooling.
  // The simpler path: call STOP.bat at the legacy install location (if any)
  // via the [UninstallRun] section's predecessor — but only for upgrades,
  // which Inno Setup handles by re-running [UninstallRun] of the previous
  // install before extracting the new one. So we leave InitializeSetup as a
  // pass-through and let the previous install's uninstaller (which is
  // automatically invoked on upgrade) run STOP.bat for us.
end;
```

- [ ] **Step 2: Append ISCC invocation to `scripts/package.ps1`**

After the Step 12 smoke test, append:

```powershell

# 13) Invoke Inno Setup compiler
$isccCandidates = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw "ISCC.exe not found. Install Inno Setup 6 from https://jrsoftware.org/isdl.php or via 'winget install JRSoftware.InnoSetup'."
}

Write-Host "[13/N] Running Inno Setup compiler ($iscc)..."
& $iscc "/DMyAppVersion=$Version" (Join-Path $PSScriptRoot "installer.iss")
if ($LASTEXITCODE -ne 0) { throw "ISCC.exe failed with exit code $LASTEXITCODE" }

$installerPath = Join-Path $out "Financial-Assistant-Setup-v$Version.exe"
if (-not (Test-Path $installerPath)) {
    throw "Inno Setup reported success but installer not found at $installerPath"
}
$installerSize = (Get-Item $installerPath).Length / 1MB
Write-Host ""
Write-Host "=== Installer built: $installerPath ($([Math]::Round($installerSize, 1)) MB) ==="
```

- [ ] **Step 3: Run end-to-end**

```powershell
.\scripts\package.ps1 -Version "1.0-test"
```

Expected: completes with "Installer built: dist\Financial-Assistant-Setup-v1.0-test.exe (NN MB)".

- [ ] **Step 4: Manual install + uninstall test**

Run the installer:

```powershell
.\dist\Financial-Assistant-Setup-v1.0-test.exe
```

1. Accept defaults, install (will go to `%LOCALAPPDATA%\Programs\FinancialAssistant\` because `PrivilegesRequired=lowest` and `DefaultDirName={autopf}` resolves to LocalAppData when not elevated). Verify Start Menu group + RUN/STOP shortcuts appear.
2. Click the launch checkbox at the end; browser opens at `http://localhost:8000`.
3. Confirm `%APPDATA%\FinancialAssistant\financial.db` was created.
4. Stop via Start Menu → "Stop Financial Assistant".
5. Uninstall via Settings → Apps. Verify install dir is gone. Verify `%APPDATA%\FinancialAssistant\financial.db` survived (intentional — DB preserved across uninstall).

- [ ] **Step 5: Commit**

```
git add scripts/installer.iss scripts/package.ps1
git commit -m "feat(packaging): Inno Setup installer + ISCC integration in package.ps1

Single .exe installer with Start Menu shortcuts (RUN/STOP/Uninstall),
optional desktop icon. Lives under %LOCALAPPDATA%\Programs (no admin
needed). The DB at %APPDATA%\FinancialAssistant\financial.db is
preserved on uninstall — friend never loses data.

The fixed AppId GUID makes future releases recognise prior installs as
upgrades, so installing v1.1 over v1.0 overwrites in place.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 14: GitHub release notes template + first v1.0 release

**Files:**
- Create: `.github/release-notes-template.md`

This task ends with the first actual release published.

- [ ] **Step 1: Create the release-notes template**

`.github/release-notes-template.md`:

```markdown
# Financial Assistant v{VERSION}

Local-first personal finance tracker. Empty DB on first run; data stored in `%APPDATA%\FinancialAssistant\financial.db` (preserved across upgrades and uninstall).

## Install

1. Download `Financial-Assistant-Setup-v{VERSION}.exe` below.
2. Double-click. If Windows shows "Windows protected your PC", click **More info** → **Run anyway** (the installer is unsigned — one-time message).
3. Accept the installer defaults. A browser window will open automatically.

## Stop / quit

* The app auto-stops after 1 hour of inactivity.
* To stop manually: Start menu → **Stop Financial Assistant**.

## Update

Download the newer installer and run it. Your data in `%APPDATA%\FinancialAssistant\` is preserved.

## What's new

* (list changes here per release)

## Known issues

* SmartScreen warning on first install (unsigned). Working as expected — click "Run anyway".

## Bug reports

If something goes wrong, attach these files from the install dir:
* `app-scripts\uvicorn-stderr.log`
* `app-scripts\start-error.log`
* `app-scripts\stop.log`
```

- [ ] **Step 2: Build the v1.0 installer**

```powershell
.\scripts\package.ps1 -Version "1.0"
```

Confirm `dist\Financial-Assistant-Setup-v1.0.exe` is built.

- [ ] **Step 3: Commit + tag**

```
git add .github/release-notes-template.md
git commit -m "docs(release): GitHub release notes template

Standardises the description on every Releases page: install steps,
SmartScreen workaround, update path, where logs live.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
git tag v1.0
git push origin main v1.0
```

- [ ] **Step 4: Create the GitHub release with the installer attached**

Write release notes by copying `.github/release-notes-template.md`, replacing `{VERSION}` with `1.0`, filling the "What's new" section with the actual content of this development cycle:

```
* Phase 3 features (budget widget, savings categories, sakura theme, CSV import)
* Portable Windows installer — embedded Python, runs on any Windows 10/11 64-bit machine without dependencies
* Auto-idle backend shutdown after 60 min, frontend heartbeat keeps the backend alive while a tab is open
* Empty-state guidance on first run
* Donut chart legend now shows percentage inline
```

Then run:

```bash
"C:\Program Files\GitHub CLI\gh.exe" release create v1.0 `
    "D:\Projects\Claude\Financial_Assistant\dist\Financial-Assistant-Setup-v1.0.exe" `
    --title "Financial Assistant v1.0" `
    --notes-file - < release-notes.md
```

(Where `release-notes.md` is the locally composed file based on the template.)

- [ ] **Step 5: Verify the release**

Visit https://github.com/Donuttouchme/Financial_Assistant/releases/latest and confirm:
* Title is "Financial Assistant v1.0"
* Description matches the template
* `Financial-Assistant-Setup-v1.0.exe` is listed as a downloadable asset
* Size matches `dist/Financial-Assistant-Setup-v1.0.exe`

- [ ] **Step 6: Final smoke test from end-user perspective**

On the dev's machine, in a fresh browser session:
1. Visit the release URL
2. Download the installer (~80-120 MB)
3. Run it (SmartScreen warning expected — click through)
4. Install, launch, verify Phase 3 UI loads
5. Quit via Start Menu → Stop, then relaunch via Start Menu → Financial Assistant. Verify the browser opens and previously-entered data is preserved.

Once verified, send the release URL to the friend.

---

## Done

All 14 tasks. Backend tests passing (108). Frontend tests passing (59). Installer published. Friend can download and run.
