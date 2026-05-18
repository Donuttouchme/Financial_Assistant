import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { CategoriesList } from "@/components/categories/CategoriesList";

function renderWith(): void {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <CategoriesList />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CategoriesList", () => {
  it("renders empty-state headers without crashing", async () => {
    renderWith();
    expect(await screen.findByText("Income")).toBeInTheDocument();
    expect(screen.getByText("Expense")).toBeInTheDocument();
    expect(screen.getByText("Savings")).toBeInTheDocument();
  });
});
