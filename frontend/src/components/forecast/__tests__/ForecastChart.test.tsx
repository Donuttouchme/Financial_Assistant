import { vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ForecastChart } from "../ForecastChart";

// recharts reads DOM dimensions which jsdom always reports as 0×0, preventing
// the SVG from being rendered. Mock the chart primitives so the SVG is present
// unconditionally at a fixed size.
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <svg width={500} height={300}>{children}</svg>
    ),
    AreaChart: ({ children }: { children: React.ReactNode }) => (
      <g>{children}</g>
    ),
    BarChart: ({ children }: { children: React.ReactNode }) => (
      <g>{children}</g>
    ),
    Area: () => null,
    Bar: () => null,
    CartesianGrid: () => null,
    XAxis: () => null,
    YAxis: () => null,
    ReferenceLine: () => null,
  };
});

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient();
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>;
}

describe("ForecastChart daily mode", () => {
  it("renders without crashing for a basic daily payload", () => {
    const { container } = render(
      wrap(
        <ForecastChart
          mode="daily"
          daily={{
            month: "2026-05",
            base_currency: "EUR",
            today: "2026-05-16",
            forecast_available: true,
            points: [
              { date: "2026-05-01", cumulative: "10", is_forecast: false },
              { date: "2026-05-16", cumulative: "160", is_forecast: false },
              { date: "2026-05-17", cumulative: "170", is_forecast: true },
              { date: "2026-05-31", cumulative: "310", is_forecast: true },
            ],
          }}
        />,
      ),
    );
    // Recharts renders an SVG. Confirm one is present.
    expect(container.querySelector("svg")).not.toBeNull();
  });
});
