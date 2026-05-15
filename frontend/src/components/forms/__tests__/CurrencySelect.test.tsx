import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CurrencySelect } from "@/components/forms/CurrencySelect";

describe("CurrencySelect", () => {
  it("renders all 31 currencies in two optgroups", () => {
    render(<CurrencySelect value="CHF" onChange={() => {}} />);
    const groups = screen.getAllByRole("group");
    expect(groups).toHaveLength(2);
    expect(groups[0]).toHaveAttribute("label", "Most used");
    expect(groups[1]).toHaveAttribute("label", "All currencies");
    const options = screen.getAllByRole("option");
    expect(options.length).toBe(31);
  });

  it("displays selected currency", () => {
    render(<CurrencySelect value="HUF" onChange={() => {}} />);
    const select = screen.getByRole("combobox");
    expect(select).toHaveValue("HUF");
  });

  it("calls onChange when selection changes", async () => {
    const user = userEvent.setup();
    let last = "";
    render(<CurrencySelect value="CHF" onChange={(v) => (last = v)} />);
    await user.selectOptions(screen.getByRole("combobox"), "EUR");
    expect(last).toBe("EUR");
  });

  it("rows include symbol + code + name", () => {
    render(<CurrencySelect value="USD" onChange={() => {}} />);
    expect(screen.getByRole("option", { name: /USD/ }).textContent).toContain("$");
    expect(screen.getByRole("option", { name: /USD/ }).textContent).toContain("USD");
  });
});
