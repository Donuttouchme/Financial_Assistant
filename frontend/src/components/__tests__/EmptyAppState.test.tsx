import { describe, expect, it, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { EmptyAppState } from "@/components/EmptyAppState";
import { resetTestState, testState } from "@/tests/handlers";

function wrap(children: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => resetTestState());

describe("EmptyAppState — currency picker", () => {
  it("shows currency dropdown defaulting to base", async () => {
    render(wrap(<EmptyAppState />));
    await waitFor(() => {
      expect(screen.getByLabelText(/default currency/i).textContent).toMatch(/CHF/);
    });
  });

  it("saving updates base currency", async () => {
    const user = userEvent.setup();
    render(wrap(<EmptyAppState />));
    await waitFor(() => {
      expect(screen.getByLabelText(/default currency/i)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByLabelText(/default currency/i));
    const huf = await screen.findByRole("option", { name: /HUF/i });
    fireEvent.click(huf);
    await user.click(screen.getByRole("button", { name: /save currency/i }));
    await waitFor(() => {
      expect(testState.settings.base_currency).toBe("HUF");
    });
  });

  it("still shows the Create first category CTA", () => {
    render(wrap(<EmptyAppState />));
    expect(screen.getByRole("link", { name: /create your first category/i })).toBeInTheDocument();
  });
});

describe("EmptyAppState — welcome message", () => {
  it("shows the welcome message and a CTA link to /categories", async () => {
    render(wrap(<EmptyAppState />));
    expect(screen.getByText(/welcome to financial assistant/i)).toBeInTheDocument();
    const cta = screen.getByRole("link", { name: /create your first category/i });
    expect(cta).toHaveAttribute("href", "/categories");
  });
});
