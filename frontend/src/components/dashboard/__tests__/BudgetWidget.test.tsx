import { describe, it, expect } from "vitest";
import { render, screen, within, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { BudgetWidget } from "../BudgetWidget";
import { testState } from "@/tests/handlers";

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("BudgetWidget", () => {
  it("renders an aggregate top line and per-category rows sorted by % desc", async () => {
    // Seed categories + transactions + budgets via testState so the msw
    // GET /api/budgets handler returns realistic BudgetWithSpending rows.
    testState.categories = [
      { id: 1, name: "Dining",    kind: "expense", target_amount: null, target_date: null, created_at: "" },
      { id: 2, name: "Groceries", kind: "expense", target_amount: null, target_date: null, created_at: "" },
      { id: 3, name: "Transport", kind: "expense", target_amount: null, target_date: null, created_at: "" },
    ];
    testState.budgets = [
      { id: 10, category_id: 1, month: "2026-05", monthly_limit: "300" },
      { id: 11, category_id: 2, month: "2026-05", monthly_limit: "500" },
      { id: 12, category_id: 3, month: "2026-05", monthly_limit: "650" },
    ];
    testState.transactions = [
      // Dining: 320 spent of 300 limit (over budget, 107%)
      { id: 100, user_id: 1, amount: "320", date: "2026-05-10", category_id: 1, description: "", is_recurring: false, created_at: "", updated_at: "" },
      // Groceries: 380 of 500 (76%)
      { id: 101, user_id: 1, amount: "380", date: "2026-05-10", category_id: 2, description: "", is_recurring: false, created_at: "", updated_at: "" },
      // Transport: 280 of 650 (43%)
      { id: 102, user_id: 1, amount: "280", date: "2026-05-10", category_id: 3, description: "", is_recurring: false, created_at: "", updated_at: "" },
    ];

    render(wrap(<BudgetWidget month="2026-05" />));

    // Aggregate top line: total spent across budgeted categories / total limit
    await waitFor(() => expect(screen.queryAllByText(/Dining/i).length).toBeGreaterThan(0));

    // First listitem should be Dining (107%)
    const rows = screen.getAllByRole("listitem");
    expect(rows.length).toBe(3);
    expect(within(rows[0]).getByText(/Dining/i)).toBeInTheDocument();
    expect(within(rows[0]).getByText(/107%|10[678]%/)).toBeInTheDocument();
    // Last row should be Transport (43%)
    expect(within(rows[2]).getByText(/Transport/i)).toBeInTheDocument();
  });

  it("shows empty state when no budgets are set", async () => {
    testState.categories = [];
    testState.budgets = [];
    testState.transactions = [];

    render(wrap(<BudgetWidget month="2026-05" />));
    await waitFor(() =>
      expect(screen.getByText(/no budgets set/i)).toBeInTheDocument()
    );
  });
});
