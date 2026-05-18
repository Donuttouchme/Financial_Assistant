import { describe, it, expect, beforeEach } from "vitest";
import {
  render, screen, fireEvent, waitFor, within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import RecurringPage from "@/pages/RecurringPage";
import { resetTestState, testState } from "@/tests/handlers";
import type { Category, RecurringSchedule } from "@/api/types";

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/recurring"]}>
        <RecurringPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function seedCategory(over: Partial<Category> = {}): Category {
  const cat: Category = {
    id: 1,
    name: "Subscriptions",
    kind: "expense",
    target_amount: null,
    target_date: null,
    created_at: new Date().toISOString(),
    ...over,
  };
  testState.categories.push(cat);
  return cat;
}

function seedSchedule(over: Partial<RecurringSchedule> = {}): RecurringSchedule {
  const id = testState.nextScheduleId++;
  const sched: RecurringSchedule = {
    id,
    transaction_id: 100 + id,
    amount: "-25.00",
    category_id: 1,
    description: "Netflix",
    currency: "CHF",
    start_date: "2026-01-01",
    next_occurrence_date: "2026-06-01",
    frequency: "monthly",
    ...over,
  };
  testState.recurringSchedules.push(sched);
  return sched;
}

describe("RecurringPage", () => {
  beforeEach(() => {
    resetTestState();
  });

  it("renders empty state when no schedules", async () => {
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByText(/no recurring schedules yet/i),
      ).toBeInTheDocument();
    });
  });

  it("renders a table row per schedule", async () => {
    seedCategory();
    seedSchedule({ description: "Netflix" });
    seedSchedule({ description: "Spotify", amount: "-12.50" });
    renderPage();
    expect(await screen.findByText("Netflix")).toBeInTheDocument();
    expect(await screen.findByText("Spotify")).toBeInTheDocument();
  });

  it("delete confirmation flow removes the schedule", async () => {
    seedCategory();
    seedSchedule({ description: "Netflix" });
    renderPage();

    expect(await screen.findByText("Netflix")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: /delete netflix/i }),
    );

    // Confirm in the AlertDialog
    const confirmBtn = await screen.findByRole("button", {
      name: /^delete$/i,
    });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(screen.queryByText("Netflix")).not.toBeInTheDocument();
    });
    expect(testState.recurringSchedules).toHaveLength(0);
  });

  it("edit dialog updates amount", async () => {
    const user = userEvent.setup();
    seedCategory();
    seedSchedule({ description: "Netflix", amount: "-500.00", currency: "CHF" });
    renderPage();

    expect(await screen.findByText("Netflix")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /edit netflix/i }));

    const dialog = await screen.findByRole("dialog");
    const amountInput = within(dialog).getByLabelText(/amount/i) as HTMLInputElement;
    expect(amountInput.value).toBe("500.00");

    await user.clear(amountInput);
    await user.type(amountInput, "600.00");

    fireEvent.click(within(dialog).getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(testState.recurringSchedules[0].amount).toBe("-600.00");
    });

    // Row reflects the new amount.
    await waitFor(() => {
      expect(screen.getByText(/600\.00/)).toBeInTheDocument();
    });
  });
});
