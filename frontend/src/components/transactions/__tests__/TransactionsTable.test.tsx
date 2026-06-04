import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { TransactionsTable } from "@/components/transactions/TransactionsTable";
import { resetTestState, testState } from "@/tests/handlers";

function wrap(children: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("TransactionsTable", () => {
  it("shows empty-state message when no transactions for month", async () => {
    render(wrap(<TransactionsTable month="2026-05" />));
    expect(
      await screen.findByText(/No transactions for this month/i),
    ).toBeInTheDocument();
  });
});

beforeEach(() => {
  resetTestState();
  testState.categories.push({
    id: 1, name: "Food", kind: "expense",
    target_amount: null, target_date: null,
    created_at: new Date().toISOString(),
  });
});

describe("TransactionsTable — multi-currency display", () => {
  it("native-currency row shows only the native amount", async () => {
    testState.transactions.push({
      id: 1, user_id: 1, amount: "12.50", date: "2026-05-14",
      category_id: 1, description: "lunch", is_recurring: false,
      currency: "CHF", base_amount: "12.50",
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    });
    render(wrap(<TransactionsTable month="2026-05" />));
    await waitFor(() => {
      expect(screen.getByText(/CHF\s*12/)).toBeInTheDocument();
    });
    expect(screen.queryByText(/≈/)).toBeNull();
  });

  it("foreign-currency row shows native primary + base secondary", async () => {
    testState.transactions.push({
      id: 1, user_id: 1, amount: "100.00", date: "2026-05-14",
      category_id: 1, description: "x", is_recurring: false,
      currency: "EUR", base_amount: "104.17",
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    });
    render(wrap(<TransactionsTable month="2026-05" />));
    await waitFor(() => {
      // EUR with de-DE locale formats as "100,00 €"; match the numeric portion
      expect(screen.getByText(/100[,.]00/)).toBeInTheDocument();
      expect(screen.getByText(/≈/)).toBeInTheDocument();
      // CHF 104.17 is in a separate div node
      expect(screen.getByText(/104[,.]17/)).toBeInTheDocument();
    });
  });

  it("shows em-dash placeholder when base_amount is null", async () => {
    testState.transactions.push({
      id: 1, user_id: 1, amount: "100.00", date: "2026-05-14",
      category_id: 1, description: "x", is_recurring: false,
      currency: "EUR", base_amount: null,
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    });
    render(wrap(<TransactionsTable month="2026-05" />));
    await waitFor(() => {
      expect(screen.getByText(/—/)).toBeInTheDocument();
    });
  });
});

describe("TransactionsTable search mode", () => {
  beforeEach(() => {
    testState.transactions.push(
      {
        id: 10, user_id: 1, amount: "10", date: "2026-01-05", category_id: 1,
        description: "lunch out", is_recurring: false, currency: "CHF",
        base_amount: "10", created_at: "", updated_at: "",
      },
      {
        id: 11, user_id: 1, amount: "20", date: "2026-05-05", category_id: 1,
        description: "dinner", is_recurring: false, currency: "CHF",
        base_amount: "20", created_at: "", updated_at: "",
      },
    );
  });

  it("renders all-months search matches when search prop is set", async () => {
    render(wrap(<TransactionsTable month="2026-05" search="lun" />));
    await waitFor(() =>
      expect(screen.getByText("lunch out")).toBeInTheDocument(),
    );
    expect(screen.queryByText("dinner")).not.toBeInTheDocument();
  });

  it("shows a search-specific empty message when nothing matches", async () => {
    render(wrap(<TransactionsTable month="2026-05" search="zzz" />));
    await waitFor(() =>
      expect(screen.getByText(/No transactions match/i)).toBeInTheDocument(),
    );
  });
});
