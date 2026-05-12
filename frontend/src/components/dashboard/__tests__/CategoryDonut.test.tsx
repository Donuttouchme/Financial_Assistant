import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { CategoryDonut } from "@/components/dashboard/CategoryDonut";

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
