import { http, HttpResponse } from "msw";
import type {
  BaseCurrencyChangePreview,
  BudgetRead,
  BudgetWithSpending,
  Category,
  FxRefreshResponse,
  FxStatusRead,
  ImportPreset,
  RecurringSchedule,
  SettingsRead,
  Transaction,
} from "@/api/types";

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

export function resetTestState() {
  testState.categories = [];
  testState.transactions = [];
  testState.budgets = [];
  testState.importPresets = [];
  testState.recurringSchedules = [];
  testState.settings = { base_currency: "CHF" };
  testState.fxStatus = { latest_date: null, source: "frankfurter.dev", is_fresh: false };
  testState.currentMonth = null;
  testState.nextCatId = 1;
  testState.nextTxId = 1;
  testState.nextPresetId = 1;
  testState.nextScheduleId = 1;
}

function fakeDailyMay2026() {
  const points = [];
  for (let day = 1; day <= 31; day++) {
    const dateStr = `2026-05-${String(day).padStart(2, "0")}`;
    points.push({
      date: dateStr,
      cumulative: String(day * 10),
      is_forecast: day > 16,
    });
  }
  return {
    month: "2026-05",
    base_currency: "EUR",
    today: "2026-05-16",
    forecast_available: true,
    points,
  };
}

const forecastHandlers = [
  http.get("/api/forecast/daily-cumulative", ({ request }) => {
    const url = new URL(request.url);
    const month = url.searchParams.get("month") ?? "2026-05";
    if (month === "2026-05") return HttpResponse.json(fakeDailyMay2026());
    return HttpResponse.json({
      month,
      base_currency: "EUR",
      today: "2026-05-16",
      forecast_available: false,
      points: [],
    });
  }),

  http.get("/api/forecast/monthly-buckets", ({ request }) => {
    const url = new URL(request.url);
    const horizon = url.searchParams.get("horizon") ?? "3m";
    const mode = url.searchParams.get("mode") ?? "centered";
    return HttpResponse.json({
      horizon, mode,
      base_currency: "EUR",
      today: "2026-05-16",
      forecast_available: true,
      points: [
        { month: "2026-04", total: "200", actual_mtd: null, forecast_remainder: null, kind: "past" },
        { month: "2026-05", total: "300", actual_mtd: "160", forecast_remainder: "140", kind: "current" },
        { month: "2026-06", total: "250", actual_mtd: null, forecast_remainder: null, kind: "future" },
      ],
    });
  }),
];

export const handlers = [
  http.get("/api/health", () =>
    HttpResponse.json({ status: "ok" }),
  ),

  http.post("/api/heartbeat", () => HttpResponse.json({ ok: true })),

  http.get("/api/categories", () =>
    HttpResponse.json(testState.categories),
  ),

  http.post("/api/categories", async ({ request }) => {
    const body = (await request.json()) as { name: string; kind?: string };
    if (testState.categories.some((c) => c.name === body.name)) {
      return HttpResponse.json(
        { detail: `Category '${body.name}' already exists` },
        { status: 400 },
      );
    }
    const kindIn = body.kind;
    const kind: Category["kind"] =
      kindIn === "income" ? "income" :
      kindIn === "savings" ? "savings" : "expense";
    const cat: Category = {
      id: testState.nextCatId++,
      name: body.name,
      kind,
      target_amount: null,
      target_date: null,
      created_at: new Date().toISOString(),
    };
    testState.categories.push(cat);
    return HttpResponse.json(cat, { status: 201 });
  }),

  http.delete("/api/categories/:id", ({ params }) => {
    const id = Number(params.id);
    const idx = testState.categories.findIndex((c) => c.id === id);
    if (idx < 0) {
      return HttpResponse.json({ detail: "not found" }, { status: 404 });
    }
    if (testState.transactions.some((t) => t.category_id === id)) {
      return HttpResponse.json(
        { detail: "Category is in use" },
        { status: 409 },
      );
    }
    testState.categories.splice(idx, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  http.get("/api/transactions", ({ request }) => {
    const url = new URL(request.url);
    const month = url.searchParams.get("month");
    const catId = url.searchParams.get("category_id");
    let rows = testState.transactions;
    if (month) rows = rows.filter((t) => t.date.startsWith(month));
    if (catId) rows = rows.filter((t) => t.category_id === Number(catId));
    return HttpResponse.json(rows);
  }),

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
        normalize(t.description ?? "") + " " + normalize(cat);
      return tokens.every((tok) => haystack.includes(tok));
    });
    return HttpResponse.json(rows);
  }),

  http.post("/api/transactions", async ({ request }) => {
    const body = (await request.json()) as {
      amount: string; date: string; category_id: number;
      description: string; is_recurring?: boolean; currency?: string;
    };
    const tx: Transaction = {
      id: testState.nextTxId++,
      user_id: 1,
      amount: body.amount,
      date: body.date,
      category_id: body.category_id,
      description: body.description,
      is_recurring: body.is_recurring ?? false,
      currency: body.currency ?? "CHF",
      base_amount: body.amount,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    testState.transactions.push(tx);
    return HttpResponse.json(tx, { status: 201 });
  }),

  http.put("/api/transactions/:id", async ({ params, request }) => {
    const id = Number(params.id);
    const idx = testState.transactions.findIndex((t) => t.id === id);
    if (idx < 0) {
      return HttpResponse.json({ detail: "not found" }, { status: 404 });
    }
    const body = (await request.json()) as Partial<{
      amount: string; date: string; category_id: number;
      description: string; is_recurring: boolean; currency: string;
    }>;
    const updated: Transaction = {
      ...testState.transactions[idx],
      ...body,
      base_amount: body.amount ?? testState.transactions[idx].base_amount,
      updated_at: new Date().toISOString(),
    };
    testState.transactions[idx] = updated;
    return HttpResponse.json(updated);
  }),

  http.delete("/api/transactions/:id", ({ params }) => {
    const id = Number(params.id);
    const idx = testState.transactions.findIndex((t) => t.id === id);
    if (idx < 0) {
      return HttpResponse.json({ detail: "not found" }, { status: 404 });
    }
    testState.transactions.splice(idx, 1);
    return new HttpResponse(null, { status: 204 });
  }),

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

  http.get("/api/budgets", ({ request }) => {
    const url = new URL(request.url);
    const month = url.searchParams.get("month");

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

    const result: BudgetWithSpending[] = budgets.map((b) => {
      const cat = testState.categories.find((c) => c.id === b.category_id);
      const spent = testState.transactions
        .filter(
          (t) =>
            t.category_id === b.category_id &&
            (!month || t.date.startsWith(month)),
        )
        .reduce((sum, t) => sum + Number(t.amount), 0);
      const limit = Number(b.monthly_limit);
      const over_budget = spent > limit;
      const overage = over_budget ? String(spent - limit) : "0";
      return {
        category_id: b.category_id,
        category_name: cat?.name ?? `Category ${b.category_id}`,
        month: b.month,
        monthly_limit: b.monthly_limit,
        spent: String(spent),
        over_budget,
        overage,
      };
    });

    return HttpResponse.json(result);
  }),

  http.get("/api/import-presets", () =>
    HttpResponse.json(testState.importPresets),
  ),

  http.post("/api/import-presets", async ({ request }) => {
    const body = (await request.json()) as {
      name: string;
      config: ImportPreset["config"];
    };
    const preset: ImportPreset = {
      id: testState.nextPresetId++,
      name: body.name,
      config: body.config,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    testState.importPresets.push(preset);
    return HttpResponse.json(preset, { status: 201 });
  }),

  http.put("/api/import-presets/:id", async ({ params, request }) => {
    const id = Number(params.id);
    const idx = testState.importPresets.findIndex((p) => p.id === id);
    if (idx < 0) {
      return HttpResponse.json({ detail: "not found" }, { status: 404 });
    }
    const body = (await request.json()) as {
      name: string;
      config: ImportPreset["config"];
    };
    const updated: ImportPreset = {
      ...testState.importPresets[idx],
      name: body.name,
      config: body.config,
      updated_at: new Date().toISOString(),
    };
    testState.importPresets[idx] = updated;
    return HttpResponse.json(updated);
  }),

  http.delete("/api/import-presets/:id", ({ params }) => {
    const id = Number(params.id);
    const idx = testState.importPresets.findIndex((p) => p.id === id);
    if (idx < 0) {
      return HttpResponse.json({ detail: "not found" }, { status: 404 });
    }
    testState.importPresets.splice(idx, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  http.get("/api/recurring", () =>
    HttpResponse.json(testState.recurringSchedules),
  ),

  http.get("/api/recurring/:id", ({ params }) => {
    const id = Number(params.id);
    const sched = testState.recurringSchedules.find((s) => s.id === id);
    if (!sched) {
      return HttpResponse.json({ detail: "schedule not found" }, { status: 404 });
    }
    return HttpResponse.json(sched);
  }),

  http.patch("/api/recurring/:id", async ({ params, request }) => {
    const id = Number(params.id);
    const idx = testState.recurringSchedules.findIndex((s) => s.id === id);
    if (idx < 0) {
      return HttpResponse.json({ detail: "schedule not found" }, { status: 404 });
    }
    const body = (await request.json()) as Partial<RecurringSchedule>;
    const updated: RecurringSchedule = {
      ...testState.recurringSchedules[idx],
      ...body,
    };
    testState.recurringSchedules[idx] = updated;
    return HttpResponse.json(updated);
  }),

  http.delete("/api/recurring/:id", ({ params }) => {
    const id = Number(params.id);
    const idx = testState.recurringSchedules.findIndex((s) => s.id === id);
    if (idx < 0) {
      return HttpResponse.json({ detail: "schedule not found" }, { status: 404 });
    }
    testState.recurringSchedules.splice(idx, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  http.get("/api/settings", () => HttpResponse.json(testState.settings)),

  http.patch("/api/settings/base_currency", async ({ request }) => {
    const body = (await request.json()) as { base_currency: string };
    testState.settings = { base_currency: body.base_currency };
    return HttpResponse.json(testState.settings);
  }),

  http.post("/api/settings/base_currency/preview", async ({ request }) => {
    const body = (await request.json()) as { base_currency: string };
    const preview: BaseCurrencyChangePreview = {
      old_base: testState.settings.base_currency,
      new_base: body.base_currency,
      budgets: testState.budgets.map((b) => ({
        category_id: b.category_id,
        category_name:
          testState.categories.find((c) => c.id === b.category_id)?.name ?? `#${b.category_id}`,
        month: b.month,
        old_amount: b.monthly_limit,
        new_amount: b.monthly_limit,
      })),
      savings_goals: [],
    };
    return HttpResponse.json(preview);
  }),

  http.post("/api/import/preview", async ({ request }) => {
    const body = (await request.json()) as { file_content: string };
    const lines = body.file_content.split("\n").filter((l) => l.trim().length > 0);
    const rows = lines.map((_, idx) => ({
      row_index: idx,
      date: "2026-05-01",
      description: `Row ${idx}`,
      amount: "-10.00",
      currency: "CHF",
      kind_hint: "expense",
      is_duplicate: false,
      errors: [],
    }));
    return HttpResponse.json({ rows });
  }),

  http.post("/api/import/commit", async ({ request }) => {
    const body = (await request.json()) as {
      selections: Array<{ row_index: number }>;
    };
    return HttpResponse.json({ imported: body.selections.length, skipped: 0 });
  }),

  http.get("/api/fx/status", () => HttpResponse.json(testState.fxStatus)),

  http.post("/api/fx/refresh", () => {
    const today = new Date().toISOString().slice(0, 10);
    testState.fxStatus = { latest_date: today, source: "frankfurter.dev", is_fresh: true };
    return HttpResponse.json<FxRefreshResponse>({
      fetched_date: today,
      currencies_updated: 31,
      ok: true,
    });
  }),

  ...forecastHandlers,

  http.get("/api/backup/download", () => {
    // Return enough bytes to be a believable SQLite file (magic header + 100 zeros).
    const bytes = new Uint8Array(116);
    const magic = new TextEncoder().encode("SQLite format 3\x00");
    bytes.set(magic, 0);
    return new HttpResponse(bytes, {
      status: 200,
      headers: {
        "Content-Type": "application/octet-stream",
        "Content-Disposition": 'attachment; filename="financial.db"',
      },
    });
  }),

  http.post("/api/backup/restore", () =>
    HttpResponse.json({ status: "restoring" }, { status: 202 }),
  ),
];
