import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import ForecastPage from "../ForecastPage";

function wrap(ui: React.ReactNode, initial = "/forecast") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initial]}>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("ForecastPage", () => {
  it("renders the 6m centered title by default", async () => {
    render(wrap(<ForecastPage />));
    await waitFor(() => {
      expect(screen.getByText(/6m \(centered on today\)/i)).toBeInTheDocument();
    });
  });

  it("shows the mode toggle when horizon ≠ 1m", async () => {
    render(wrap(<ForecastPage />, "/forecast?horizon=3m"));
    await waitFor(() => {
      expect(
        screen.getByRole("radiogroup", { name: /forecast mode/i }),
      ).toBeInTheDocument();
    });
  });

  it("hides the mode toggle when horizon = 1m", async () => {
    render(wrap(<ForecastPage />, "/forecast?horizon=1m"));
    await waitFor(() => {
      expect(
        screen.queryByRole("radiogroup", { name: /forecast mode/i }),
      ).toBeNull();
    });
  });
});
