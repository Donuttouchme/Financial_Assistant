import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { ForecastWidget } from "../ForecastWidget";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/dashboard"]}>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("ForecastWidget", () => {
  it("renders the card title", async () => {
    render(wrap(<ForecastWidget month="2026-05" />));
    await waitFor(() => {
      expect(screen.getByText(/this month/i)).toBeInTheDocument();
    });
  });

  it("links to the full forecast page", async () => {
    render(wrap(<ForecastWidget month="2026-05" />));
    await waitFor(() => {
      const link = screen.getByRole("link", { name: /see full forecast/i });
      expect(link.getAttribute("href")).toContain("/forecast");
    });
  });
});
