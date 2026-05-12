import { http, HttpResponse } from "msw";
import type {
  BudgetWithSpending,
  Category,
  Transaction,
} from "@/api/types";

export const testState = {
  categories: [] as Category[],
  transactions: [] as Transaction[],
  budgets: [] as BudgetWithSpending[],
  nextCatId: 1,
  nextTxId: 1,
};

export function resetTestState() {
  testState.categories = [];
  testState.transactions = [];
  testState.budgets = [];
  testState.nextCatId = 1;
  testState.nextTxId = 1;
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

  http.get("/api/budgets", () =>
    HttpResponse.json(testState.budgets),
  ),
];
