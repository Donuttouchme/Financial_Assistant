import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { TransactionFormDialog } from "@/components/transactions/TransactionFormDialog";

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

describe("TransactionFormDialog", () => {
  it("renders in create mode without crashing", async () => {
    render(
      wrap(
        <TransactionFormDialog
          mode="create"
          open
          onOpenChange={() => {}}
        />,
      ),
    );
    expect(await screen.findByText("Add transaction")).toBeInTheDocument();
    expect(screen.getByLabelText(/amount/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/monthly recurring/i)).toBeInTheDocument();
  });

  it("renders in edit mode with the Update button and no recurring switch", async () => {
    render(
      wrap(
        <TransactionFormDialog
          mode="edit"
          open
          onOpenChange={() => {}}
          transaction={{
            id: 7,
            user_id: 1,
            amount: "12.34",
            date: "2026-05-10",
            category_id: 1,
            description: "Milk",
            is_recurring: false,
            created_at: "",
            updated_at: "",
          }}
        />,
      ),
    );
    expect(await screen.findByText("Edit transaction")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /update/i })).toBeInTheDocument();
    expect(screen.queryByLabelText(/monthly recurring/i)).not.toBeInTheDocument();
  });
});
