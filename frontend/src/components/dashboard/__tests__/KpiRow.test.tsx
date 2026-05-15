import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { KpiRow } from "@/components/dashboard/KpiRow";
import { resetTestState, testState } from "@/tests/handlers";

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("KpiRow", () => {
  it("renders Income, Expense, Net, Saved", async () => {
    render(wrap(<KpiRow month="2026-05" />));
    expect(await screen.findByText("Income")).toBeInTheDocument();
    expect(screen.getByText("Expense")).toBeInTheDocument();
    expect(screen.getByText("Net")).toBeInTheDocument();
    expect(screen.getByText("Saved")).toBeInTheDocument();
    expect(screen.queryByText(/Over budget/i)).toBeNull();
  });

  it("sums income/expense using base_amount, not native amount", async () => {
    resetTestState();
    testState.categories.push(
      { id: 1, name: "Salary", kind: "income",  target_amount: null, target_date: null, created_at: "" },
      { id: 2, name: "Food",   kind: "expense", target_amount: null, target_date: null, created_at: "" },
    );
    // 1000 EUR with base_amount 1041.67 CHF
    testState.transactions.push({
      id: 1, user_id: 1, amount: "1000", date: "2026-05-01",
      category_id: 1, description: "", is_recurring: false,
      currency: "EUR", base_amount: "1041.67",
      created_at: "", updated_at: "",
    });
    // 12.50 CHF expense
    testState.transactions.push({
      id: 2, user_id: 1, amount: "12.50", date: "2026-05-02",
      category_id: 2, description: "", is_recurring: false,
      currency: "CHF", base_amount: "12.50",
      created_at: "", updated_at: "",
    });
    render(wrap(<KpiRow month="2026-05" />));
    await waitFor(() => {
      // Income shows 1041.67 CHF (the base_amount, not 1000 EUR).
      // CHF formats as "CHF 1'041.67" (de-CH locale, apostrophe thousands sep).
      // Match any character that may appear between 1 and 041.
      const matches = screen.getAllByText(/1.?041[.,]67/);
      expect(matches.length).toBeGreaterThan(0);
    });
  });

  it("skips transactions with null base_amount", async () => {
    resetTestState();
    testState.categories.push({
      id: 1, name: "Salary", kind: "income", target_amount: null, target_date: null, created_at: "",
    });
    testState.transactions.push({
      id: 1, user_id: 1, amount: "1000", date: "2026-05-01",
      category_id: 1, description: "", is_recurring: false,
      currency: "EUR", base_amount: null,
      created_at: "", updated_at: "",
    });
    render(wrap(<KpiRow month="2026-05" />));
    await waitFor(() => {
      // All 4 KPI cards should show CHF 0.00 (income skipped due to null base_amount)
      const zeros = screen.getAllByText(/CHF\s*0[.,]00/);
      expect(zeros.length).toBeGreaterThanOrEqual(1);
      // Specifically the Income card label should still be present
      expect(screen.getByText("Income")).toBeInTheDocument();
    });
  });
});
