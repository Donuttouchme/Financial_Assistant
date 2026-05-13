import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { TransactionFormDialog } from "@/components/transactions/TransactionFormDialog";
import { testState } from "@/tests/handlers";

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

describe("TransactionFormDialog savings flow", () => {
  beforeEach(() => {
    testState.categories = [
      {
        id: 99,
        name: "Vacation 2027",
        kind: "savings",
        target_amount: "3000.00",
        target_date: "2027-06-30",
        created_at: new Date().toISOString(),
      },
    ];
  });

  it("shows Deposit/Withdraw toggle when picked category is kind=savings", async () => {
    render(
      wrap(
        <TransactionFormDialog mode="create" open onOpenChange={() => {}} />,
      ),
    );

    // Wait for the dialog to render.
    expect(await screen.findByText("Add transaction")).toBeInTheDocument();

    // No toggle visible before a category is picked.
    expect(screen.queryByRole("group", { name: /direction/i })).toBeNull();

    // Open category select and pick the savings category.
    const trigger = screen.getByRole("combobox");
    fireEvent.click(trigger);
    const opt = await screen.findByRole("option", {
      name: /vacation 2027 \(savings\)/i,
    });
    fireEvent.click(opt);

    // Wait for the Direction group to appear after the category is selected.
    await waitFor(() => {
      expect(
        screen.getByRole("group", { name: /direction/i }),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByRole("radio", { name: /deposit/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("radio", { name: /withdraw/i }),
    ).toBeInTheDocument();
  });

  it("infers withdraw direction from negative amount in edit mode", async () => {
    render(
      wrap(
        <TransactionFormDialog
          mode="edit"
          open
          onOpenChange={() => {}}
          transaction={{
            id: 10,
            user_id: 1,
            amount: "-50.00",
            date: "2026-05-10",
            category_id: 99,
            description: "Withdrawal",
            is_recurring: false,
            created_at: "",
            updated_at: "",
          }}
        />,
      ),
    );

    expect(await screen.findByText("Edit transaction")).toBeInTheDocument();

    // The amount input should show the absolute value.
    const amountInput = screen.getByLabelText(/amount/i) as HTMLInputElement;
    expect(amountInput.value).toBe("50");

    // Wait for categories to load, then the Direction group should appear.
    await waitFor(() => {
      expect(
        screen.getByRole("group", { name: /direction/i }),
      ).toBeInTheDocument();
    });

    const withdrawBtn = screen.getByRole("radio", { name: /withdraw/i });
    expect(withdrawBtn).toBeInTheDocument();
    expect(withdrawBtn).toHaveAttribute("aria-checked", "true");
  });
});
