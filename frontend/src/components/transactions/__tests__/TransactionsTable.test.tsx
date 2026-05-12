import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { TransactionsTable } from "@/components/transactions/TransactionsTable";

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

describe("TransactionsTable", () => {
  it("shows empty-state message when no transactions for month", async () => {
    render(wrap(<TransactionsTable month="2026-05" />));
    expect(
      await screen.findByText(/No transactions for this month/i),
    ).toBeInTheDocument();
  });
});
