import { http, HttpResponse } from "msw";
import type {
  BudgetRead,
  BudgetWithSpending,
  Category,
  ImportPreset,
  Transaction,
} from "@/api/types";

export const testState = {
  categories: [] as Category[],
  transactions: [] as Transaction[],
  budgets: [] as BudgetRead[],
  importPresets: [] as ImportPreset[],
  nextCatId: 1,
  nextTxId: 1,
  nextPresetId: 1,
};

export function resetTestState() {
  testState.categories = [];
  testState.transactions = [];
  testState.budgets = [];
  testState.importPresets = [];
  testState.nextCatId = 1;
  testState.nextTxId = 1;
  testState.nextPresetId = 1;
}

export const handlers = [
  http.get("/api/health", () =>
    HttpResponse.json({ status: "ok" }),
  ),

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
    const cat: Category = {
      id: testState.nextCatId++,
      name: body.name,
      kind: (body.kind === "income" ? "income" : "expense"),
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

  http.post("/api/transactions", async ({ request }) => {
    const body = (await request.json()) as {
      amount: string; date: string; category_id: number;
      description: string; is_recurring?: boolean;
    };
    const tx: Transaction = {
      id: testState.nextTxId++,
      user_id: 1,
      amount: body.amount,
      date: body.date,
      category_id: body.category_id,
      description: body.description,
      is_recurring: body.is_recurring ?? false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    testState.transactions.push(tx);
    return HttpResponse.json(tx, { status: 201 });
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

  http.get("/api/budgets", ({ request }) => {
    const url = new URL(request.url);
    const month = url.searchParams.get("month");

    const budgets = month
      ? testState.budgets.filter((b) => b.month === month)
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
];
