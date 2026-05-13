import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ImportConfigPanel } from "../ImportConfigPanel";
import type { CsvImportConfig } from "@/api/types";

const defaultConfig: CsvImportConfig = {
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

describe("ImportConfigPanel", () => {
  it("calls onChange when delimiter changes", () => {
    const onChange = vi.fn();
    render(<ImportConfigPanel config={defaultConfig} onChange={onChange} />);
    fireEvent.click(screen.getByLabelText(/delimiter/i));
    fireEvent.click(screen.getByRole("option", { name: "," }));
    expect(onChange).toHaveBeenCalled();
    const calls = onChange.mock.calls;
    const next = calls[calls.length - 1][0];
    expect(next.delimiter).toBe(",");
  });
});
