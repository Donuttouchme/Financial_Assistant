import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { MonthlyTrendBar } from "@/components/dashboard/MonthlyTrendBar";

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

describe("MonthlyTrendBar", () => {
  it("renders the card title even when empty", async () => {
    render(wrap(<MonthlyTrendBar month="2026-05" />));
    expect(
      await screen.findByText(/Last 6 months/i),
    ).toBeInTheDocument();
  });
});
