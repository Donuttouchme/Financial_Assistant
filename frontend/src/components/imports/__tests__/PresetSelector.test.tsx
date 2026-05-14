import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PresetSelector } from "../PresetSelector";
import type { CsvImportConfig } from "@/api/types";

const config: CsvImportConfig = {
  delimiter: ";",
  decimal_sep: ".",
  thousands_sep: "",
  date_format: "%Y-%m-%d",
  skip_header_rows: 0,
  has_header: false,
  amount_format: "signed",
  sign_convention: "negative_is_expense",
  cols: { date: 0, description: 1, amount: 2 },
};

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{node}</QueryClientProvider>;
}

describe("PresetSelector", () => {
  it("renders 'Save as preset' control", () => {
    render(wrap(<PresetSelector currentConfig={config} onLoad={() => {}} />));
    expect(screen.getByText(/save as preset/i)).toBeInTheDocument();
  });

  it("renders 'Load preset' label and a select", () => {
    render(wrap(<PresetSelector currentConfig={config} onLoad={() => {}} />));
    expect(screen.getByText(/load preset/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/load preset/i)).toBeInTheDocument();
  });
});
