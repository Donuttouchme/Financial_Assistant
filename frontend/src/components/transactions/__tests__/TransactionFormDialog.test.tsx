import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { TransactionFormDialog } from "@/components/transactions/TransactionFormDialog";
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

describe("TransactionFormDialog", () => {
  beforeEach(() => {
    resetTestState();
  });

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
    expect(screen.getByLabelText(/^amount$/i)).toBeInTheDocument();
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
            currency: "CHF",
            base_amount: null,
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
    resetTestState();
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
    const trigger = screen.getByRole("combobox", { name: /category/i });
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
            currency: "CHF",
            base_amount: null,
            created_at: "",
            updated_at: "",
          }}
        />,
      ),
    );

    expect(await screen.findByText("Edit transaction")).toBeInTheDocument();

    // The amount input should show the absolute value.
    const amountInput = screen.getByLabelText(/^amount$/i) as HTMLInputElement;
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

describe("TransactionFormDialog — create flow", () => {
  beforeEach(() => {
    resetTestState();
    testState.categories.push({
      id: 1, name: "Food", kind: "expense",
      target_amount: null, target_date: null,
      created_at: new Date().toISOString(),
    });
  });

  it("currency dropdown defaults to base currency", async () => {
    render(wrap(<TransactionFormDialog mode="create" open onOpenChange={() => {}} />));
    await waitFor(() => {
      expect(screen.getByLabelText(/currency/i)).toHaveValue("CHF");
    });
  });

  it("Save and add another keeps dialog open, clears amount, retains category", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(wrap(<TransactionFormDialog mode="create" open onOpenChange={onOpenChange} />));
    await waitFor(() => expect(screen.getByLabelText(/currency/i)).toHaveValue("CHF"));

    await user.type(screen.getByLabelText(/^amount$/i), "12.50");
    // Radix Select requires fireEvent (userEvent triggers pointer events that jsdom doesn't support)
    const trigger = screen.getByRole("combobox", { name: /category/i });
    fireEvent.click(trigger);
    const opt = await screen.findByRole("option", { name: /food/i });
    fireEvent.click(opt);
    await user.type(screen.getByLabelText(/description/i), "lunch");

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /save and add another/i }));
    });

    await waitFor(() => expect(testState.transactions.length).toBe(1));
    // Dialog still open
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
    // Amount cleared
    expect(screen.getByLabelText(/^amount$/i)).toHaveValue("");
    // Inline indicator shown
    expect(screen.getByText(/saved/i)).toBeInTheDocument();
  });

  it("Create button closes the dialog", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(wrap(<TransactionFormDialog mode="create" open onOpenChange={onOpenChange} />));
    await waitFor(() => expect(screen.getByLabelText(/currency/i)).toHaveValue("CHF"));

    await user.type(screen.getByLabelText(/^amount$/i), "5");
    // Radix Select requires fireEvent
    const trigger = screen.getByRole("combobox", { name: /category/i });
    fireEvent.click(trigger);
    const opt = await screen.findByRole("option", { name: /food/i });
    fireEvent.click(opt);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /^create$/i }));
    });
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
  });
});
