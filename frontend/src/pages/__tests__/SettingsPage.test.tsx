import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import SettingsPage from "@/pages/SettingsPage";

function wrap(children: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("SettingsPage", () => {
  it("renders three sections", () => {
    render(wrap(<SettingsPage />));
    expect(screen.getByRole("heading", { name: /currency/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /exchange rates/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /appearance/i })).toBeInTheDocument();
  });
});
