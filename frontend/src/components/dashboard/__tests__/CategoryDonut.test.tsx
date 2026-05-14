import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { CategoryDonut } from "@/components/dashboard/CategoryDonut";
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

describe("CategoryDonut", () => {
  it("renders the empty-state when no expenses", async () => {
    render(wrap(<CategoryDonut month="2026-05" />));
    expect(
      await screen.findByText(/No expense transactions/i),
    ).toBeInTheDocument();
  });
});

describe("CategoryDonut legend", () => {
  beforeEach(() => {
    resetTestState();
    testState.categories = [
      { id: 1, name: "Groceries", kind: "expense", target_amount: null, target_date: null, created_at: "2026-05-01T00:00:00" },
      { id: 2, name: "Eating-out", kind: "expense", target_amount: null, target_date: null, created_at: "2026-05-01T00:00:00" },
    ];
    testState.transactions = [
      { id: 1, user_id: 1, amount: "75", description: "", date: "2026-05-10", category_id: 1, is_recurring: false, created_at: "", updated_at: "" },
      { id: 2, user_id: 1, amount: "25", description: "", date: "2026-05-11", category_id: 2, is_recurring: false, created_at: "", updated_at: "" },
    ];
  });

  it("legend shows category name plus percent for each slice", async () => {
    render(wrap(<CategoryDonut month="2026-05" />));
    await waitFor(() => {
      expect(screen.getByText(/Groceries/)).toBeInTheDocument();
      expect(screen.getByText(/Eating-out/)).toBeInTheDocument();
      expect(screen.getByText(/75%/)).toBeInTheDocument();
      expect(screen.getByText(/25%/)).toBeInTheDocument();
    });
  });
});
