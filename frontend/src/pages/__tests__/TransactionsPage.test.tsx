import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import TransactionsPage from "../TransactionsPage";
import { resetTestState } from "@/tests/handlers";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/transactions?month=2026-05"]}>
        <TransactionsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TransactionsPage empty state", () => {
  beforeEach(() => {
    resetTestState();
  });

  it("shows EmptyAppState when there are no categories", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/welcome to financial assistant/i)).toBeInTheDocument();
    });
  });
});
