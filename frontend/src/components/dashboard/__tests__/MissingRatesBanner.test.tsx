import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { MissingRatesBanner } from "@/components/dashboard/MissingRatesBanner";
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

describe("MissingRatesBanner", () => {
  it("renders nothing when all transactions have a base_amount", async () => {
    resetTestState();
    testState.categories.push({
      id: 1, name: "Salary", kind: "income", target_amount: null, target_date: null, created_at: "",
    });
    testState.transactions.push({
      id: 1, user_id: 1, amount: "1000", date: "2026-05-01",
      category_id: 1, description: "", is_recurring: false,
      currency: "EUR", base_amount: "1041.67",
      created_at: "", updated_at: "",
    });
    const { container } = render(wrap(<MissingRatesBanner month="2026-05" />));
    // Give the query a tick
    await new Promise((r) => setTimeout(r, 30));
    expect(container.textContent).not.toMatch(/excluded/i);
  });

  it("shows the count and a Settings link when transactions have null base_amount", async () => {
    resetTestState();
    testState.categories.push({
      id: 1, name: "Salary", kind: "income", target_amount: null, target_date: null, created_at: "",
    });
    testState.transactions.push(
      {
        id: 1, user_id: 1, amount: "100", date: "2026-05-01",
        category_id: 1, description: "", is_recurring: false,
        currency: "EUR", base_amount: null,
        created_at: "", updated_at: "",
      },
      {
        id: 2, user_id: 1, amount: "50", date: "2026-05-02",
        category_id: 1, description: "", is_recurring: false,
        currency: "USD", base_amount: null,
        created_at: "", updated_at: "",
      },
    );
    render(wrap(<MissingRatesBanner month="2026-05" />));
    await waitFor(() => {
      expect(screen.getByText(/2/)).toBeInTheDocument();
      expect(screen.getByText(/transactions are excluded/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: /refresh in settings/i })).toHaveAttribute("href", "/settings");
  });
});
