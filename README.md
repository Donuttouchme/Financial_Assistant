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
