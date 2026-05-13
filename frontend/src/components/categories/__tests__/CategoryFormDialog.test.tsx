import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CategoryFormDialog } from "@/components/categories/CategoryFormDialog";

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{node}</QueryClientProvider>;
}

describe("CategoryFormDialog", () => {
  it("shows target fields when kind switches to savings", async () => {
    render(wrap(<CategoryFormDialog open onOpenChange={() => {}} />));

    // Initial: kind defaults to expense — no target fields visible.
    expect(screen.queryByLabelText(/target amount/i)).toBeNull();
    expect(screen.queryByLabelText(/target date/i)).toBeNull();

    // Open the kind Select and click Savings.
    const kindTrigger = screen.getByLabelText(/kind/i);
    fireEvent.click(kindTrigger);
    fireEvent.click(await screen.findByRole("option", { name: /savings/i }));

    expect(screen.getByLabelText(/target amount/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/target date/i)).toBeInTheDocument();
  });
});
