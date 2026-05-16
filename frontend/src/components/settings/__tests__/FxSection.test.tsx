import { describe, expect, it, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { FxSection } from "@/components/settings/FxSection";
import { resetTestState, testState } from "@/tests/handlers";

function wrap(children: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

beforeEach(() => resetTestState());

describe("FxSection", () => {
  it("shows 'not yet fetched' when latest_date is null", async () => {
    render(wrap(<FxSection />));
    await waitFor(() => {
      expect(screen.getByText(/not yet fetched/i)).toBeInTheDocument();
    });
  });

  it("shows the latest date when present", async () => {
    const today = new Date().toISOString().slice(0, 10);
    testState.fxStatus = { latest_date: today, source: "frankfurter.dev", is_fresh: true };
    render(wrap(<FxSection />));
    await waitFor(() => {
      expect(screen.getByText(new RegExp(today))).toBeInTheDocument();
    });
  });

  it("refresh button triggers refresh", async () => {
    const user = userEvent.setup();
    render(wrap(<FxSection />));
    await user.click(screen.getByRole("button", { name: /refresh rates/i }));
    await waitFor(() => {
      expect(testState.fxStatus.is_fresh).toBe(true);
    });
  });
});
