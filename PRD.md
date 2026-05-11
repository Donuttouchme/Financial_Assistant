# Financial Assistant - Product Requirements Document

## Problem Statement

User needs a simple way to track monthly income and expenditures to maintain visibility over their personal finances. Currently, tracking happens manually or is scattered across different tools, making it difficult to see spending patterns, budget against categories, and understand overall financial health.

## Solution

Build a single-user web-based financial tracking application that:
- Runs locally during development (backend on localhost:8000, frontend on localhost:3000)
- Migrates to a web server for production deployment
- Provides a browser-based UI for adding, viewing, and analyzing transactions
- Automatically generates recurring transactions (monthly subscriptions, salary, rent)
- Tracks income and expenditures by category
- Alerts user when spending exceeds budgets
- Exports transaction data to CSV

## User Stories

1. As a user, I want to add a new transaction (income or expenditure), so that I can record my financial activity
2. As a user, I want to specify an amount, date, category, and description for each transaction, so that I have complete financial records
3. As a user, I want to mark a transaction as recurring (monthly), so that I don't have to manually enter salary, rent, and subscriptions each month
4. As a user, I want the app to automatically generate recurring transactions on the appropriate date, so that I have a complete picture of expected monthly activity
5. As a user, I want to create custom categories, so that I can organize transactions in a way that matches my financial reality
6. As a user, I want to see all my transactions in a list view, so that I can review my activity
7. As a user, I want to filter transactions by month, so that I can analyze spending patterns over time
8. As a user, I want to filter transactions by category, so that I can see spending in specific areas
9. As a user, I want to edit existing transactions, so that I can correct mistakes or update information
10. As a user, I want to delete transactions, so that I can remove incorrect entries
11. As a user, I want to see my spending visualized in charts/graphs, so that I can quickly understand where money is going
12. As a user, I want to set a monthly budget for each category, so that I can control spending
13. As a user, I want to see budget alerts on the dashboard, so that I know when I've exceeded budget limits
14. As a user, I want to export my transactions to CSV, so that I can use the data in spreadsheets or other tools
15. As a user, I want the app to persist my data locally, so that my financial information remains private and accessible
16. As a user, I want the app to be responsive and fast, so that tracking transactions doesn't feel burdensome
17. As a user, I want clear error messages, so that I understand what went wrong when something fails
18. As a user, I want a simple README explaining how to set up and run the app locally, so that I can get started quickly
19. As a user, I want the app to be ready for multi-user deployment later, so that architectural changes aren't needed later

## Implementation Decisions

### Technology Stack
- **Backend:** Python 3.10+ with FastAPI framework
- **Frontend:** React 18+ with modern hooks
- **Database:** SQLite for local development, PostgreSQL for production
- **State Management:** React Context API for single-user state
- **API Style:** RESTful with auto-generated OpenAPI/Swagger documentation
- **Deployment:** Backend and frontend run separately in development (Option A), unified on web server for production
- **Automation:** Windows batch files for local start/stop operations
- **Repository:** Monorepo structure with `/backend` and `/frontend` folders

### Data Model

**Core Entities:**
- **User** — Single user initially, but user_id included in all queries for future multi-user support
- **Transaction** — amount (decimal), date, category (foreign key), description (text), user_id, created_at, updated_at
- **Category** — name (string), user_id (enables custom categories), created_at
- **RecurringSchedule** — transaction_id (foreign key), frequency ("monthly"), start_date, next_occurrence_date, user_id
- **BudgetLimit** — category_id, user_id, monthly_limit (decimal), month (YYYY-MM format)

### API Contract

**Transactions:**
- `POST /api/transactions` — Create transaction
- `GET /api/transactions?month=YYYY-MM&category_id=X` — List transactions with filters
- `PUT /api/transactions/{id}` — Update transaction
- `DELETE /api/transactions/{id}` — Delete transaction

**Categories:**
- `GET /api/categories` — List all user categories
- `POST /api/categories` — Create custom category
- `DELETE /api/categories/{id}` — Delete category (if no transactions reference it)

**Budgets:**
- `PUT /api/budgets/{category_id}` — Set monthly budget for category
- `GET /api/budgets?month=YYYY-MM` — Get all budgets for a month

**Export:**
- `GET /api/export/csv?month=YYYY-MM` — Export transactions as CSV

**Health:**
- `GET /api/health` — Service status check

### Recurring Transaction Logic

- When a transaction is marked as recurring (monthly), a `RecurringSchedule` record is created
- A background job (or eager generation on app startup) checks for recurring schedules where `next_occurrence_date <= today`
- For each match, a new Transaction is created and `next_occurrence_date` is incremented by one month
- This enables automatic rent/salary/subscription entries without user intervention

### Validation & Error Handling

- **Frontend validation:** Required fields, amount > 0, date not in future (unless specified), category exists
- **Backend validation:** Duplicate checks, data type validation, authorization checks (user_id match)
- **Error responses:** Consistent JSON format with error code and human-readable message
- **HTTP status codes:** 200/201 (success), 400 (validation), 401 (auth), 404 (not found), 500 (server error)

### Budget Alerts

- Dashboard displays categories where current month spending > budget limit
- Alert UI shows category name, budget, current spending, and overage amount
- Calculated on-demand (no separate alert storage needed)

### Multi-User Preparation

- All queries filter by `user_id` even though single-user initially
- User context passed through API (header or session) to be replaced with auth later
- No authentication layer implemented yet, but queries are designed to support it

## Testing Decisions

### Testing Strategy

A good test focuses on **external behavior, not implementation details**. Tests should:
- Exercise the public interface (API endpoints, function signatures)
- Verify correct output for given inputs
- Not mock internal dependencies unless they're external services
- Be readable and maintainable long-term

### Modules to Test

**Backend (Python with pytest):**
- **Models & Validation** — Test Transaction, Category, BudgetLimit creation and constraints
- **TransactionService** — Test create, update, delete, filter by month/category operations
- **RecurringTransactionService** — Test recurring schedule creation, next occurrence calculation, auto-generation logic
- **BudgetService** — Test budget creation, overage calculation
- **CategoryService** — Test custom category creation/deletion
- **API Routes** — Integration tests for all REST endpoints (using TestClient)

**Frontend (React with Vitest/Jest):**
- **API Client** — Test successful requests, error handling, request/response transformation
- **Utils** — Test date formatting, currency formatting, budget calculations
- **Components** — Smoke tests only (render without crashing); skip detailed UI tests for MVP

### Testing Approach

- Use pytest for backend unit and integration tests
- Use Vitest or Jest for frontend utility and API client tests
- No UI component testing initially (can add Playwright/Cypress later)
- Aim for 70%+ coverage on business logic (services, utils), lower bar for utilities
- Tests live alongside code in `/backend/tests` and `/frontend/src/__tests__`

## Out of Scope

- **Multi-user authentication & authorization** — Design prepared but not implemented
- **Mobile app** — Web browser only for MVP
- **Mobile responsiveness** — Desktop-first UI
- **Bank API integration** — Manual entry only
- **Notifications** — Budget alerts only in UI, no emails/SMS
- **Data encryption** — Local SQLite, unencrypted
- **Audit logging** — No transaction history/change log
- **Advanced reporting** — CSV export only, no custom report builder
- **Currency support** — Single currency only
- **Scheduled recurring transactions** — Monthly frequency only (no weekly/daily)
- **Transaction matching/reconciliation** — No bank reconciliation features
- **Shared access** — Single-user only

## Further Notes

### Development Workflow

- **Local Setup:** Virtual environment, separate backend (FastAPI dev server) and frontend (React dev server)
- **Automation:** Windows batch files (`start.bat`, `stop.bat`) orchestrate both servers
- **GitHub Readiness:** Monorepo structure enables eventual GitHub push; `.gitignore` should exclude venv, node_modules, SQLite DB, `.env`

### Deployment Strategy

- **Phase 1 (Current):** Local SQLite + localhost
- **Phase 2 (Production):** PostgreSQL on web server, backend serves built React as static files
- **Migration Path:** No code changes needed for database swap (abstracted via SQLAlchemy ORM)

### Documentation

- **README:** Setup instructions, how to start/stop locally, basic feature overview
- **API Docs:** Auto-generated by FastAPI (Swagger UI at `/docs`)
- **Code Comments:** Minimal; focus on "why" for non-obvious logic (e.g., recurring schedule calculation)

### MVP Timeline

Target: 2-3 weeks to working MVP
- Week 1: Backend API + React components for CRUD
- Week 2: Recurring logic, charts, budget alerts
- Week 3: Testing, documentation, polish
