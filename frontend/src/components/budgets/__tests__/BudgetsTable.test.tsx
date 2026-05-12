import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { BudgetsTable } from "@/components/budgets/BudgetsTable";

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

describe("BudgetsTable", () => {
  it("shows the empty-categories message when no expense categories exist", async () => {
    render(wrap(<BudgetsTable month="2026-05" />));
    expect(
      await screen.findByText(/No expense categories yet/i),
    ).toBeInTheDocument();
  });
});
