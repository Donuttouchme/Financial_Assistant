import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SavingsGoalsRow } from "../SavingsGoalsRow";
import { testState } from "@/tests/handlers";

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{node}</QueryClientProvider>;
}

describe("SavingsGoalsRow", () => {
  it("renders one card per savings category with a target", async () => {
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

    render(wrap(<SavingsGoalsRow month="2026-05" />));
    expect(await screen.findByText(/Vacation 2027/i)).toBeInTheDocument();
  });

  it("renders nothing when there are no savings categories", async () => {
    testState.categories = [
      {
        id: 1,
        name: "Groceries",
        kind: "expense",
        target_amount: null,
        target_date: null,
        created_at: new Date().toISOString(),
      },
    ];

    const { container } = render(wrap(<SavingsGoalsRow month="2026-05" />));
    // After hooks resolve, the component returns null — container should have no section
    await new Promise(r => setTimeout(r, 50));
    expect(container.querySelector("section")).toBeNull();
  });
});
