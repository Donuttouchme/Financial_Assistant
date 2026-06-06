# Recurring Budgets + Theme-Aware Saved Banner

**Status:** approved, ready for implementation
**Date:** 2026-06-06
**Target release:** v1.3.3 (patch)

## Goal

Two small, related UX fixes that surfaced after v1.3.2 was installed.

1. **Recurring budgets.** Treat budgets as set-once-and-applies-forward. Setting "Groceries = 500" should affect every later month until the user changes it. Past months keep the limit that was in effect when they were tracked.
2. **Theme-aware Saved banner.** The green "Saved — enter the next one" banner that appears between Save-and-add-another submissions on the Add-Transaction dialog uses hardcoded Tailwind emerald shades, which read poorly on cyberpunk, sakura, emerald-dark, and navy-light themes. Replace with theme-aware tokens.

## Non-goals

- No per-month override system. The pure recurring model handles the common case; one-off Decembers can wait.
- No "schedule a change for a future month" UI. The implicit "effective from current month" matches the user's set-and-forget mental model.
- No DB schema migration. The existing `budget_limits.month` column can be reinterpreted as `effective_month` without changing column names or types.
- No new `--success` semantic token across all 6 themes. `bg-primary/10` is sufficient for one banner.

## Data model (no DB schema change)

`budget_limits` table stays exactly as it is — same columns, same unique constraint `(user_id, category_id, month)`. The semantic meaning of the `month` column changes from "this is the limit for exactly this month" to **"this is the limit effective from this month forward, until a later row supersedes it."**

To make the new semantics clear in code without breaking schema field names that the frontend already consumes:

- Keep the Python attribute on `BudgetLimit` named `month`. Add a class-level docstring stating the new convention: *"`month` is the effective-from month: this limit applies from this month forward until a later row for the same category supersedes it."*
- Keep `BudgetRead` and `BudgetWithSpending` schemas unchanged. They still expose `month` so the frontend renderer (`BudgetsTable`, `BudgetWidget`) doesn't need a field rename.
- `BudgetSet` (the PUT request body) drops the `month` field — see API section.

Renaming the column or attribute everywhere is a churn multiplier for no functional gain; the docstring carries the semantic shift.

### Forward-compatibility of existing data

Existing rows are trivially compatible. A user who set Groceries=500 for `month=2026-06` before the change automatically gets Groceries=500 for July, August, ... under the new lookup, because the row's `effective_month` is now 2026-06 and there's no later row to supersede it.

The duplicate-rows case (user set the same value in May and June) is also fine: the lookup picks the latest by `effective_month`; identical consecutive values are silently redundant but not buggy.

## Lookup semantics

In `budget_service.list_budgets_with_spending(user_id, month=M)`, the budget-row query becomes "for each category, pick the most recent effective row at or before M":

```sql
-- Pseudo-SQL; actual implementation uses SQLAlchemy with a window or a
-- correlated subquery.
SELECT b.category_id, b.monthly_limit
FROM budget_limits b
WHERE b.user_id = :u
  AND b.effective_month <= :M
  AND b.effective_month = (
    SELECT MAX(b2.effective_month)
    FROM budget_limits b2
    WHERE b2.user_id = b.user_id
      AND b2.category_id = b.category_id
      AND b2.effective_month <= :M
  )
```

The FX-adjusted spending subquery (the formula fixed in v1.2.1) is unchanged.

If no row exists with `effective_month <= M` for a given category, that category has no historical budget at month M; the table renders "—" with a "Set" action button. This is the correct retrospective behavior — viewing March 2025 should not show a limit you only first set in June 2026.

## API

`PUT /api/budgets/{category_id}`:

- **Old payload:** `{ "month": "YYYY-MM", "monthly_limit": "X.XX" }`
- **New payload:** `{ "monthly_limit": "X.XX" }`

The backend stamps `effective_month = today's YYYY-MM (UTC)` server-side. This matches the "set forward from now" UX and removes a foot-gun where the client could write a row with `effective_month` in the past and silently rewrite history.

A `datetime` boundary helper is injected via FastAPI dependency for testability (the existing `app/dependencies.py` pattern). Tests pass a fixed clock.

`GET /api/budgets?month=YYYY-MM` is unchanged on the surface; internally calls the new lookup. The response shape gains nothing new; each row still carries `monthly_limit`, `spent`, `over_budget`, `overage`, `category_id`, `category_name`, and `month` (the queried month, not the effective month — preserved for backwards compatibility with the frontend renderer).

## UI

### BudgetsTable + BudgetsPage

- The Edit/Set button flow is preserved as-is. The user types an amount, hits Save, and the server stamps the current month as `effective_month`.
- One helper sentence added directly below the page heading: *"Limits set here apply from this month forward. Past months keep their original values."* This makes the new model self-explanatory.
- The month picker on `BudgetsPage` stays. Its job becomes "audit any past month against the limit that was in effect then" rather than "edit that month's limit in isolation." This is the user-approved choice.
- No new editing affordance for "effective from" — explicit dates can come later if needed.

### Dashboard `BudgetWidget`

No change. It queries the current month via the same endpoint and gets the right effective limit.

### Saved banner fix (TransactionFormDialog.tsx:208-216)

Replace:

```tsx
className="flex items-center gap-2 rounded-md bg-emerald-100 dark:bg-emerald-900 px-3 py-2 text-sm"
```

with:

```tsx
className="flex items-center gap-2 rounded-md border border-primary/30 bg-primary/10 text-foreground px-3 py-2 text-sm"
```

Why this works for every theme:

- Every theme block in `frontend/src/index.css` defines `--primary` and `--foreground`. The banner background becomes a 10%-opacity wash of the theme's primary accent and the text becomes the theme's foreground — both always contrast correctly.
- The `CheckCircle2` icon picks up `currentColor` via `text-foreground`.
- No new tokens to add.

## Testing

### Backend

New tests in `backend/tests/test_routes/test_budgets.py` (or a sibling `test_budgets_recurring.py` if cleaner):

1. Setting Groceries=500 with frozen-clock=2026-05-15, then Groceries=600 with frozen-clock=2026-06-10 → `GET ?month=2026-05` returns 500; `?month=2026-06` and `?month=2026-07` return 600.
2. Setting a limit with frozen-clock=2026-06 → `GET ?month=2026-03` returns no row for that category (no retro carry-back).
3. Existing tests that PUT a `month` field need their payloads updated and their assertions adjusted; the dropped `month` field is no longer accepted (validation error if sent).
4. Unique-constraint behavior: two PUTs in the same calendar month for the same category overwrite the same row (matches today's upsert behavior).

### Frontend

- Update MSW handler in `frontend/src/tests/handlers.ts` for `PUT /api/budgets/:id` to reject `month` in body and expect just `monthly_limit`.
- `BudgetsTable.test.tsx`: assert the mutation payload sent on Save no longer includes `month`.
- Light render test for the Saved banner (in `TransactionFormDialog.test.tsx`): after the Save-and-add-another path, the banner is rendered with the expected class string. Visual contrast under different themes is not unit-testable; verified manually during the run skill / smoke test.

## Release

Bump `backend/app/main.py` `FastAPI(version="...")` to `1.3.3`. Bump `frontend/package.json` to `1.3.3`. Build installer via `scripts/package.ps1 -Version "1.3.3"`. Standard release flow: tag, push, draft GH release, attach `dist/Financial-Assistant-Setup-v1.3.3.exe`, publish.

## What this does NOT touch

- Recurring transactions, schedules, forecast model — unchanged.
- FX conventions — unchanged (the v1.2.1 fix stands).
- Other themes / theme picker / favicon — unchanged.

## Open questions

None at design time. If the per-month override appetite comes back later, a `budget_overrides(user_id, category_id, month, monthly_limit)` companion table can layer on top without touching the recurring model.
