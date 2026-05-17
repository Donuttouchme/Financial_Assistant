# Financial Assistant

A local-first personal finance tracker. Multi-currency, theme-aware, single-user. Ships as a one-click Windows installer; runs entirely on your machine — no accounts, no cloud, no telemetry.

**Latest release:** [v1.2.0](https://github.com/Donuttouchme/Financial_Assistant/releases/latest) — forecast graph, per-category drill-down, two new themes.

---

## What's new in v1.2.0

- **Forecast graph.** The dashboard now shows a cumulative month-to-date expense curve with a translucent forecast tail through the end of the current month. A new **Forecast** page (sidebar) lets you change horizon (1m / 3m / 6m / 1y / 2y) and switch between "centered on today" and "forecast only" views.
- **Per-category drill-down.** Filter the forecast by category from a dropdown on both the dashboard widget and the Forecast page. The selection is bookmarkable via `?category=` in the URL.
- **Two new themes.** **Emerald-dark** (forest-at-midnight, softer corners, faint film grain) and **Navy-light** (classic-banker, crisper corners, faint pinstripe). Switch from Settings → Appearance.

### Upgrade notes
- No schema migrations. The forecast feature reads existing transactions only.
- The previous "Last 6 months" bar chart on the dashboard has been replaced by the new forecast widget. The same monthly-bar view is available on the new Forecast page at horizon = 6m (with a forecast tail).

### Known limitations
- Forecast accuracy needs at least 30 days of expense data before any forecast tail appears, and at least 60 days before the per-category day-of-month profile kicks in. Below those thresholds, the chart shows what it can with a footer hint.

---

## What it does

- **Transactions.** Track income, expense, and savings entries with date, category, description, and currency. Recurring schedules auto-spawn each month.
- **Categories & budgets.** Organize spending into custom categories and set per-category monthly limits with progress and overrun alerts.
- **Savings goals.** Mark a category as savings, give it a target amount and date, and watch cumulative progress on the dashboard.
- **Multi-currency.** Enter transactions in any of 31 ISO 4217 currencies sourced from the European Central Bank (via `frankfurter.dev`). The dashboard converts everything to your chosen base currency at the date of each transaction.
- **Dashboard.** Monthly KPIs (income / expense / net / saved), category donut, six-month trend bar, budget progress, recent activity, savings goals, and a banner when FX rates are missing for any row.
- **CSV import / export.** Bring in transactions from a bank statement with per-row currency mapping or a per-file default; export with native + base-currency amounts and the rate used.
- **Settings page.** Switch base currency (with a conversion preview for existing budgets and goals), check FX freshness, refresh rates manually, pick a theme.
- **Themes.** Light, Dark, Sakura, Cyberpunk. Every UI control — dropdowns, date pickers, popovers, scrollbars — is theme-aware via custom Radix components. The browser tab favicon also adapts.
- **Portable database.** Your data lives in `%APPDATA%\FinancialAssistant\financial.db` and survives every reinstall.

---

## Install (Windows)

Download the latest installer from the [releases page](https://github.com/Donuttouchme/Financial_Assistant/releases/latest) and run it:

```
Financial-Assistant-Setup-v1.2.0.exe
```

The installer is unsigned, so SmartScreen will warn on first run — click "More info" → "Run anyway". Install location defaults to `%LOCALAPPDATA%\Programs\FinancialAssistant`. A Start Menu shortcut is created automatically; tick the optional checkbox during install if you want a Desktop icon as well.

Launching from the shortcut starts the bundled Python backend on `127.0.0.1:8000` and opens your default browser to the app. Closing the browser does not stop the backend — use the bundled `STOP.bat` (also in the Start Menu) or wait for the 60-minute idle watchdog to shut it down.

### First-run notes

- You'll land on the welcome screen. Pick a default currency (Settings → Currency lets you change it later) and create your first category.
- Existing v1.0.x users: your data carries over automatically because the DB lives in `%APPDATA%`. The app will show a one-time v1.1 migration notice on first launch.

---

## Developer setup

### Prerequisites

- **Python** 3.10+ (tested on 3.14.2)
- **Node** 18+
- **PowerShell** (Windows) or Bash (other platforms)
- **Inno Setup 6** — only needed to build installers (`winget install JRSoftware.InnoSetup`)

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

### Dev mode (hot reload)

```powershell
cd frontend
npm run dev:all
```

Starts FastAPI on `:8000` and Vite on `:3000` in one terminal, color-coded. Open `http://localhost:3000`. Ctrl+C stops both.

### Production build + installer

```powershell
.\scripts\package.ps1 -Version "1.2.0"
```

Runs the frontend production build, downloads the Python 3.14 embeddable distribution (cached after the first run), installs backend dependencies into it, and compiles the Inno Setup script. The resulting installer lands at `dist\Financial-Assistant-Setup-v1.2.0.exe` (~23 MB).

### Updating the logo / installer icon

The Start Menu shortcut, installer `.exe`, and Add/Remove Programs all use `scripts\financial-assistant.ico`. After editing `frontend\public\favicon.svg`, regenerate the matching `.ico`:

```powershell
backend\.venv\Scripts\python.exe scripts\generate_icon.py
```

---

## Architecture

### Backend (`backend/`)

- **FastAPI** 0.136 + **SQLAlchemy 2.0** (Mapped/`mapped_column` style) + **Pydantic v2**.
- **SQLite** for storage. Migrations are lightweight `ALTER TABLE ADD COLUMN` statements driven by `migrations.py` and run on lifespan startup — no Alembic needed.
- **`httpx`** for the `frankfurter.dev` FX client. Rates are fetched once per business day (lifespan kickoff, non-blocking) and on demand via `POST /api/fx/refresh`. Errors are swallowed so the app remains usable offline.
- **Conversion**. Transactions store native `amount` + `currency`. The base-currency `base_amount` is computed at read time from the `fx_rates` table using EUR as the pivot, so changing the base currency doesn't require re-snapshotting historical rows.

### Frontend (`frontend/`)

- **React 18** + **TypeScript** (strict) + **Vite 5**.
- **shadcn/ui** components on **Radix UI** primitives, styled with **Tailwind 3**. Color tokens are CSS variables driven by a class on `<html>` (`.dark`, `.sakura`, `.cyberpunk`).
- **TanStack Query 5** for server state. **react-hook-form 7** + **zod 3** for forms. **Recharts** for visualizations. **sonner** for toasts.
- **MSW 2** for frontend test mocking; **Vitest** + Testing Library for the test runner.

### Distribution (`scripts/`)

- `package.ps1` — full pipeline (frontend build → embed Python → pip install → Inno compile).
- `installer.iss` — Inno Setup config (per-user install, no admin required).
- `start.ps1` / `stop.ps1` — launcher and shutdown scripts bundled into the installer.
- `portable/RUN.bat`, `STOP.bat`, `README.txt` — friend-facing files that ship at the install root.

---

## Project layout

```
Financial_Assistant/
├── backend/
│   ├── app/
│   │   ├── models/         SQLAlchemy models (transactions, fx_rate, settings, …)
│   │   ├── schemas/        Pydantic v2 request/response schemas
│   │   ├── services/       Business logic (transaction, fx, settings, budget, …)
│   │   ├── routers/        FastAPI routers (one per resource)
│   │   ├── main.py         App entrypoint + lifespan
│   │   └── migrations.py   Column-add migrations
│   ├── tests/              pytest suite (152 tests)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/            HTTP clients + types
│   │   ├── hooks/queries/  TanStack Query hooks
│   │   ├── components/     Page-scoped + shared components
│   │   │   ├── ui/         shadcn primitives
│   │   │   ├── forms/      CurrencySelect, DatePicker
│   │   │   ├── settings/   Currency / FX / Appearance sections
│   │   │   ├── dashboard/  Widgets
│   │   │   └── …
│   │   ├── pages/          Route-level pages
│   │   ├── lib/            money formatting, currencies, utils
│   │   └── tests/          MSW handlers
│   └── package.json
├── scripts/
│   ├── package.ps1         Build pipeline
│   ├── installer.iss       Inno Setup script
│   ├── start.ps1 / stop.ps1
│   ├── generate_icon.py    Regenerate financial-assistant.ico
│   └── portable/           Files staged at the install root
└── docs/                   Plans, ADRs, PRD
```

---

## Configuration

The backend reads two env vars from `backend/.env` (or the process environment):

| Variable        | Default                           | Purpose                                                       |
|-----------------|-----------------------------------|---------------------------------------------------------------|
| `DATABASE_URL`  | `sqlite:///./financial.db`        | SQLAlchemy connection string. Overridden by `FA_DB_PATH`.    |
| `FA_DB_PATH`    | (unset in dev, set in installer)  | Absolute path to the SQLite file. The installer's launcher sets this to `%APPDATA%\FinancialAssistant\financial.db` so reinstalls don't touch your data. |

---

## API

The backend serves the SPA at `/` and the API at `/api/*`. Swagger UI at `http://localhost:8000/docs`.

| Method | Path                                       | Purpose                                         |
|--------|--------------------------------------------|-------------------------------------------------|
| GET    | `/api/health`                              | Service status                                  |
| GET    | `/api/settings`                            | Get current base currency                       |
| POST   | `/api/settings/base_currency/preview`      | Preview budget/goal conversion at a new base    |
| PATCH  | `/api/settings/base_currency`              | Commit base-currency change (409 if rates missing) |
| GET    | `/api/fx/status`                           | Latest fetched rate date + freshness            |
| POST   | `/api/fx/refresh`                          | Force-refresh from ECB                          |
| GET    | `/api/categories`                          | List categories                                 |
| POST   | `/api/categories`                          | Create (`kind=expense\|income\|savings`)       |
| DELETE | `/api/categories/{id}`                     | Delete (409 if referenced)                      |
| GET    | `/api/transactions?month&category_id`      | List, filtered                                  |
| POST   | `/api/transactions`                        | Create (auto-seeds recurring schedule)          |
| PUT    | `/api/transactions/{id}`                   | Update                                          |
| DELETE | `/api/transactions/{id}`                   | Delete                                          |
| GET    | `/api/budgets?month`                       | Budgets + spent + overage                       |
| PUT    | `/api/budgets/{category_id}`               | Upsert monthly limit                            |
| POST   | `/api/import/preview`                      | Parse a CSV without saving                      |
| POST   | `/api/import/commit`                       | Import selected rows                            |
| GET    | `/api/export/csv?month`                    | Download CSV                                    |

---

## Tests

```powershell
# Backend (152 tests)
cd backend
.\.venv\Scripts\Activate.ps1
pytest

# Frontend (111 tests)
cd frontend
npm test
```

Backend tests use an autouse fixture (`backend/tests/conftest.py`) that monkeypatches the FX HTTP client to a no-op. Tests that exercise the real client opt in with the `real_fx_client` pytest marker.

---

## Roadmap

Tracked loosely; PRs welcome.

### Near term (next minor)
- **Recurring schedule UI** — view, edit, and stop schedules without deleting the originating transaction.
- **In-app backup / restore** — export the SQLite database to a chosen folder and restore from a `.db` file.
- **Annual report view** — yearly summary with year-over-year comparison.
- **Better mobile layout** — current dashboard is desktop-first.

### Longer term
- **Multi-user.** The schema already carries `user_id` everywhere; introducing real auth (e.g. local password or OIDC) won't require a schema migration. Settings would become per-user.
- **Three-decimal currency precision.** BHD, KWD, OMR, TND are stored at 2-decimal precision today; minor refactor of `Numeric(12, 2)` columns once anyone asks.
- **Linux / macOS installers.** The build pipeline is Windows-only today (Inno Setup). A platform-neutral container or `.app` bundle is feasible.
- **Plaid / bank API integration.** Currently CSV import is the only on-ramp. Direct bank sync would replace it for users who can authenticate.

### Out of scope
- **Multi-tenant SaaS.** This app is intentionally local-first. No cloud sync, no shared accounts.
- **Investment tracking.** Stocks, crypto, retirement accounts are out of scope. Use a dedicated tool.

---

## Releases & versioning

The project follows [Semantic Versioning](https://semver.org/). Release notes live at `dist/release-notes-v*.md` in each release and are also attached to the corresponding GitHub Release.

| Version | Date       | Highlights                                                  |
|---------|------------|-------------------------------------------------------------|
| [v1.1.0](https://github.com/Donuttouchme/Financial_Assistant/releases/tag/v1.1.0) | 2026-05-16 | Multi-currency, Settings page, Cyberpunk theme, custom date/currency pickers, theme-aware favicon. |
| [v1.0.1](https://github.com/Donuttouchme/Financial_Assistant/releases/tag/v1.0.1) | 2026-05-14 | Packaging fix (em-dash in `start.ps1`).                     |
| [v1.0](https://github.com/Donuttouchme/Financial_Assistant/releases/tag/v1.0)     | 2026-05-13 | First public release — categories, transactions, budgets, dashboard, CSV import/export, portable installer. (Superseded — install v1.0.1 or later.) |

---

## Contributing

This is a personal project, but issues and small PRs are welcome. For anything non-trivial, open an issue first to discuss scope.

- Backend code follows existing service-layer conventions (`db: Session` first arg, services commit themselves, `user_id` filtered everywhere).
- Frontend follows shadcn/Radix patterns. Avoid native `<select>` / `<input type="date">` — they don't honor `color-scheme` on Windows Chromium, so the project standardizes on Radix Select and the bundled `DatePicker`.
- Tests are required for new behavior, optional for cosmetic-only changes.

---

## License

Personal-use license; not yet packaged for redistribution. If you're interested in using this for something else, [open an issue](https://github.com/Donuttouchme/Financial_Assistant/issues).
