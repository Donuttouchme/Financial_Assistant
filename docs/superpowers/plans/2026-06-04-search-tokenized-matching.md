# Tokenized Search Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make multi-word transaction searches like `"Media Markt"` find concatenated text like `"MediaMarkt"` (and vice-versa), regardless of word order or punctuation.

**Architecture:** Replace the single whole-query casefold substring match in `transaction_service.search_transactions` with a **token-AND** match: split the query on whitespace into words; every word must appear (as a normalized substring) in the transaction's description or category. Normalization casefolds and keeps only alphanumerics (`str.isalnum()`, which preserves accented á/é/ő/ű and digits while dropping spaces and punctuation), so `Media Markt`/`MediaMarkt`/`Media-Markt` all collapse to `mediamarkt`. Description and category are joined with a NUL separator so a word can't match across the field boundary. The MSW test double is updated to mirror this logic.

**Tech Stack:** Backend — Python/FastAPI, SQLAlchemy, pytest. Frontend — React/TS, TanStack Query, Vitest 2, MSW 2.

## Behavior (the contract)

- `"Media Markt"` matches description `"MediaMarkt"` (token AND + normalization).
- `"mediamarkt"` matches description `"Media Markt"` (reverse direction).
- `"Markt Media"` matches `"MediaMarkt"` (order-independent).
- `"spar market"` matches `"Spar-Market 2026"` (punctuation ignored).
- `"Media Aldi"` does NOT match `"MediaMarkt"` (every word required).
- A word may match in description OR category, but a single word cannot span the description↔category boundary.
- Unchanged: all-months scope, date-desc ordering, ≥2-char activation gate, the endpoint/hooks/header.

## File structure

- Modify `backend/app/services/transaction_service.py` — add module-level `_normalize` helper; rewrite `search_transactions` body. (One responsibility: search.)
- Modify `backend/tests/test_transaction_service.py` — add token-matching tests.
- Modify `frontend/src/tests/handlers.ts` — mirror the tokenized logic in the `/api/transactions/search` MSW handler.
- Modify `frontend/src/hooks/queries/__tests__/useSearchTransactions.test.tsx` — add a multi-word test.

## Commands reference

- Backend tests (Bash, shared venv): `cd "/d/Projects/Claude/Financial_Assistant/.claude/worktrees/search-tokenize/backend" && "/d/Projects/Claude/Financial_Assistant/backend/.venv/Scripts/python.exe" -m pytest -q <args>`
- Frontend tests: `cd "/d/Projects/Claude/Financial_Assistant/.claude/worktrees/search-tokenize/frontend" && npm test -- --run <path>`
- Baseline: backend 237 passing, frontend 157 passing.

---

### Task 1: Backend token-AND matching

**Files:**
- Modify: `backend/app/services/transaction_service.py` — add `_normalize` above `search_transactions` (which starts at line 186); rewrite the `search_transactions` body.
- Test: `backend/tests/test_transaction_service.py` — append after `test_search_short_query_returns_empty`.

- [ ] **Step 1: Append the failing tests** to `backend/tests/test_transaction_service.py` (the file imports `from datetime import date`, `from decimal import Decimal`, and `from app.services import ... transaction_service`; it has a `db_session` fixture):

```python
def _seed_one(db_session, *, description, name="Food"):
    from app.models.category import Category
    from app.services import transaction_service as svc

    cat = Category(user_id=1, name=name, kind="expense")
    db_session.add(cat)
    db_session.commit()
    svc.create_transaction(
        db_session, user_id=1, amount=Decimal("10"),
        tx_date=date(2026, 1, 5), category_id=cat.id,
        description=description, currency="CHF",
    )


def test_search_multiword_matches_concatenated_text(db_session):
    from app.services import transaction_service as svc

    _seed_one(db_session, description="MediaMarkt purchase")
    results = svc.search_transactions(db_session, user_id=1, q="Media Markt")
    assert len(results) == 1


def test_search_single_word_query_matches_spaced_text(db_session):
    from app.services import transaction_service as svc

    _seed_one(db_session, description="Media Markt")
    results = svc.search_transactions(db_session, user_id=1, q="mediamarkt")
    assert len(results) == 1


def test_search_words_can_be_reordered(db_session):
    from app.services import transaction_service as svc

    _seed_one(db_session, description="MediaMarkt")
    results = svc.search_transactions(db_session, user_id=1, q="Markt Media")
    assert len(results) == 1


def test_search_ignores_punctuation(db_session):
    from app.services import transaction_service as svc

    _seed_one(db_session, description="Spar-Market 2026")
    assert len(svc.search_transactions(db_session, user_id=1, q="spar market")) == 1
    assert len(svc.search_transactions(db_session, user_id=1, q="media.markt")) == 0


def test_search_requires_all_words(db_session):
    from app.services import transaction_service as svc

    _seed_one(db_session, description="MediaMarkt")
    assert svc.search_transactions(db_session, user_id=1, q="Media Aldi") == []


def test_search_word_spans_description_and_category(db_session):
    from app.services import transaction_service as svc

    _seed_one(db_session, description="weekly shop", name="Groceries")
    results = svc.search_transactions(db_session, user_id=1, q="grocer shop")
    assert len(results) == 1


def test_search_word_cannot_span_field_boundary(db_session):
    from app.services import transaction_service as svc

    _seed_one(db_session, description="buy media", name="rket club")
    assert svc.search_transactions(db_session, user_id=1, q="mediarket") == []
```

- [ ] **Step 2: Run the new tests and confirm they FAIL**

Run: `... -m pytest -q tests/test_transaction_service.py -k "multiword or reordered or punctuation or all_words or spans or span_field or spaced_text"`
Expected: FAIL — the current whole-query substring match can't match across spaces (e.g. `"Media Markt" not in "mediamarkt purchase"`).

- [ ] **Step 3: Add the `_normalize` helper** to `backend/app/services/transaction_service.py`, immediately ABOVE the `def search_transactions(` line (line 186):

```python
def _normalize(text: str) -> str:
    """Casefold and keep only letters/digits.

    str.isalnum() keeps accented Unicode letters (á/é/ő/ű) and digits while
    dropping spaces and punctuation, so "Media-Markt"/"Media Markt"/"MediaMarkt"
    all collapse to "mediamarkt".
    """
    return "".join(c for c in text.casefold() if c.isalnum())


```

- [ ] **Step 4: Replace the `search_transactions` body.** Replace the entire existing function (docstring + body, lines 186–228) with:

```python
def search_transactions(
    db: Session,
    *,
    user_id: int,
    q: str,
) -> list[Transaction]:
    """All-months search. Splits the query into whitespace-separated words and
    requires EVERY word to appear (as a normalized substring) in the
    transaction's description or category name.

    _normalize casefolds and strips spaces/punctuation, so multi-word queries
    match concatenated text in either direction ("Media Markt" <-> "MediaMarkt")
    and word order doesn't matter. Matching is done in Python (not SQL LIKE) so
    accented Hungarian letters fold correctly. Data volume is single-user and
    modest.

    Returns [] for queries shorter than 2 non-whitespace chars (defensive; the
    frontend gates at 2 chars too).
    """
    stripped = q.strip()
    if len(stripped) < 2:
        return []
    tokens = [w for w in (_normalize(word) for word in stripped.split()) if w]
    if not tokens:
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
        # NUL separator keeps a query word from matching across the
        # description<->category boundary (no normalized token contains NUL).
        haystack = (
            _normalize(t.description or "")
            + "\x00"
            + _normalize(cat_names.get(t.category_id, ""))
        )
        if all(token in haystack for token in tokens):
            out.append(t)
    return out
```

- [ ] **Step 5: Run the full search test subset and confirm PASS** (the 5 prior search tests + 7 new = 12):

Run: `... -m pytest -q tests/test_transaction_service.py -k search`
Expected: PASS (12 passed). The pre-existing tests (`test_search_matches_description_case_insensitive`, `..._accented_text_with_casefold`, `..._category_name`, `..._ignores_month_and_orders_date_desc`, `..._short_query_returns_empty`) must remain green.

- [ ] **Step 6: Commit** (from worktree root `D:\Projects\Claude\Financial_Assistant\.claude\worktrees\search-tokenize`):

```bash
git add backend/app/services/transaction_service.py backend/tests/test_transaction_service.py
git commit -m "feat(search): token-AND matching with space/punctuation normalization"
```

---

### Task 2: Mirror tokenized logic in the MSW test double

**Files:**
- Modify: `frontend/src/tests/handlers.ts` — replace the `GET /api/transactions/search` handler.
- Test: `frontend/src/hooks/queries/__tests__/useSearchTransactions.test.tsx` — add a multi-word test.

- [ ] **Step 1: Add the failing test** to `frontend/src/hooks/queries/__tests__/useSearchTransactions.test.tsx`. The file already has a `beforeEach` that seeds category `{id:1, name:"Food"}` and transaction `{id:1, description:"lunch out", ...}`, plus a `wrap()` helper and `import { resetTestState, testState } from "@/tests/handlers"`. Add this test inside the existing `describe("useSearchTransactions", ...)` block:

```tsx
  it("matches a spaced query against concatenated text", async () => {
    testState.transactions.push({
      id: 2, user_id: 1, amount: "30", date: "2026-02-02", category_id: 1,
      description: "MediaMarkt TV", is_recurring: false, currency: "CHF",
      base_amount: "30", created_at: "", updated_at: "",
    });
    const { result } = renderHook(() => useSearchTransactions("Media Markt"), {
      wrapper: wrap(),
    });
    await waitFor(() => expect(result.current.data?.length).toBe(1));
    expect(result.current.data?.[0].description).toBe("MediaMarkt TV");
  });
```

- [ ] **Step 2: Run and confirm FAIL**

Run: `npm test -- --run src/hooks/queries/__tests__/useSearchTransactions.test.tsx`
Expected: FAIL — the current MSW handler does a whole-query `.toLowerCase().includes()`, so `"media markt"` is not a substring of `"mediamarkt tv"` → 0 results.

- [ ] **Step 3: Replace the MSW handler** in `frontend/src/tests/handlers.ts`. Replace the existing block:

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

with:

```ts
  http.get("/api/transactions/search", ({ request }) => {
    const url = new URL(request.url);
    const raw = (url.searchParams.get("q") ?? "").trim();
    if (raw.length < 2) return HttpResponse.json([]);
    const normalize = (s: string) =>
      s.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
    const tokens = raw.split(/\s+/).map(normalize).filter(Boolean);
    if (tokens.length === 0) return HttpResponse.json([]);
    const rows = testState.transactions.filter((t) => {
      const cat =
        testState.categories.find((c) => c.id === t.category_id)?.name ?? "";
      const haystack =
        normalize(t.description ?? "") + " " + normalize(cat);
      return tokens.every((tok) => haystack.includes(tok));
    });
    return HttpResponse.json(rows);
  }),
```

- [ ] **Step 4: Run and confirm PASS**

Run: `npm test -- --run src/hooks/queries/__tests__/useSearchTransactions.test.tsx`
Expected: PASS (3 passed — the 2 existing + 1 new). Then run the other search-dependent suites to confirm no regression:
`npm test -- --run src/components/transactions/__tests__/TransactionsTable.test.tsx`
Expected: PASS (existing `"lun"` match and `"zzz"` empty-message tests still green).

- [ ] **Step 5: Commit** (from worktree root):

```bash
git add frontend/src/tests/handlers.ts frontend/src/hooks/queries/__tests__/useSearchTransactions.test.tsx
git commit -m "test(search): mirror token-AND matching in MSW handler"
```

---

### Task 3: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Full backend suite** — `... -m pytest -q` → expected 244 passed (237 baseline + 7 new).
- [ ] **Step 2: Full frontend suite** — `npm test -- --run` → expected 158 passed (157 baseline + 1 new).
- [ ] **Step 3: Typecheck + build** — `npm run build` → `tsc -b` clean, vite build succeeds.

---

## Self-review notes

- **Spec coverage:** concatenation both directions → `test_search_multiword_matches_concatenated_text` + `test_search_single_word_query_matches_spaced_text`; reordering → `test_search_words_can_be_reordered`; punctuation → `test_search_ignores_punctuation`; AND semantics → `test_search_requires_all_words`; cross-field word → `test_search_word_spans_description_and_category`; field-boundary guard → `test_search_word_cannot_span_field_boundary`; frontend mirror → the MSW test. ≥2 gate and accented casefold are preserved by the retained pre-existing tests.
- **Type consistency:** `_normalize(text: str) -> str` defined once and used in both the query-token path and the haystack path. MSW `normalize` mirrors it. Function signature `search_transactions(db, *, user_id, q)` unchanged — no caller/route changes needed.
- **Out of scope (not built):** fuzzy/edit-distance matching, per-word minimum length, amount/numeric search, ranking/relevance ordering.
