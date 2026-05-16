import { describe, expect, it, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CurrencySection } from "@/components/settings/CurrencySection";
import { resetTestState, testState } from "@/tests/handlers";

function wrap(children: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

beforeEach(() => resetTestState());

describe("CurrencySection", () => {
  it("shows current base currency", async () => {
    render(wrap(<CurrencySection />));
    await waitFor(() => {
      expect(screen.getByLabelText(/base currency/i).textContent).toMatch(/CHF/);
    });
  });

  it("change button is disabled when value equals current base", async () => {
    render(wrap(<CurrencySection />));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /change base currency/i })).toBeDisabled();
    });
  });

  it("opens preview dialog when changing to a different currency", async () => {
    const user = userEvent.setup();
    render(wrap(<CurrencySection />));
    await waitFor(() => {
      expect(screen.getByLabelText(/base currency/i).textContent).toMatch(/CHF/);
    });
    fireEvent.click(screen.getByLabelText(/base currency/i));
    fireEvent.click(await screen.findByRole("option", { name: /EUR/i }));
    await user.click(screen.getByRole("button", { name: /change base currency/i }));
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText(/changing CHF to EUR/i)).toBeInTheDocument();
    });
  });

  it("confirm in dialog commits the change", async () => {
    const user = userEvent.setup();
    render(wrap(<CurrencySection />));
    await waitFor(() => expect(screen.getByLabelText(/base currency/i)).toBeInTheDocument());
    fireEvent.click(screen.getByLabelText(/base currency/i));
    fireEvent.click(await screen.findByRole("option", { name: /HUF/i }));
    await user.click(screen.getByRole("button", { name: /change base currency/i }));
    await waitFor(() => screen.getByRole("dialog"));
    await user.click(screen.getByRole("button", { name: /confirm/i }));
    await waitFor(() => {
      expect(testState.settings.base_currency).toBe("HUF");
    });
  });
});
