# Financial Assistant

Personal finance tracker — single user, local-first. CHF-denominated. FastAPI backend, React frontend, SQLite.

---

## Two ways to run

### A) End-user (one click)

Goal: open the app like any other program. No terminals.

1. **One-time setup (developer does this):** see "Developer setup" below.
2. **Daily use:** double-click the "Financial Assistant" shortcut on the desktop.
   The default browser opens to `http://localhost:8000` with the app loaded.
   To stop the server: open Task Manager → find `python.exe` → End task.

### B) Developer mode (hot reload)

```powershell
cd frontend
npm run dev:all
```

This launches the FastAPI backend on `:8000` and the Vite frontend on `:3000` in one terminal, color-coded. Browse to `http://localhost:3000`. Ctrl+C stops both.

---

## Developer setup

### Prerequisites
- Python 3.10+ (project tested on 3.14.2)
- Node 18+
- PowerShell (Windows) or Bash (other platforms)

### One-time install

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
deactivate
cd ..

# Frontend
cd frontend
npm install
cd ..
```

### Build the production bundle (run after frontend changes)

```powershell
scripts\build.bat
```

This creates `frontend/dist/`, which the backend's StaticFiles mount serves in spouse mode.

### Create the desktop shortcut (one time, per machine)

1. Right-click the desktop → New → Shortcut.
2. Location:
   ```
   powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "<full-path>\scripts\start.ps1"
   ```
   Replace `<full-path>` with the absolute repo path.
3. Name: "Financial Assistant".

---

## Stack

- **Backend:** FastAPI, SQLAlchemy 2.0, SQLite, Pydantic v2
- **Frontend:** React 18, TypeScript, Vite, TanStack Query, shadcn/ui, Tailwind, Recharts
- **Tests:** pytest (backend), Vitest + msw (frontend API + utils)

## API

The backend serves the SPA at `/` and the API at `/api/*`. OpenAPI interactive docs at `http://localhost:8000/docs`.

| Method | Path                               | Purpose                        |
|--------|------------------------------------|--------------------------------|
| GET    | /api/health                        | Service status                 |
| GET    | /api/categories                    | List categories                |
| POST   | /api/categories                    | Create category (kind=expense\|income) |
| DELETE | /api/categories/{id}               | Delete (409 if in use)         |
| GET    | /api/transactions?month&category_id| List, filtered                 |
| POST   | /api/transactions                  | Create (auto-seeds recurring)  |
| PUT    | /api/transactions/{id}             | Update                         |
| DELETE | /api/transactions/{id}             | Delete                         |
| PUT    | /api/budgets/{category_id}         | Upsert monthly limit           |
| GET    | /api/budgets?month                 | Budgets + spent + overage      |
| GET    | /api/export/csv?month              | Download CSV                   |

## Tests

```powershell
# Backend
cd backend
.\.venv\Scripts\Activate.ps1
pytest -v
pytest --cov=app --cov-report=term-missing

# Frontend
cd frontend
npm test
```

## Recurring transactions

When a transaction is created with `is_recurring: true`, a `RecurringSchedule` is seeded with `next_occurrence_date = date + 1 month`. On app startup the lifespan hook materializes every overdue schedule. Stopping recurring = deleting the original template transaction (past auto-generated entries stay).

## Multi-currency / Multi-user

Out of scope for v1. Currency hardcoded to CHF; `user_id` filtered everywhere with a hardcoded `1` so introducing auth later won't require schema changes.
