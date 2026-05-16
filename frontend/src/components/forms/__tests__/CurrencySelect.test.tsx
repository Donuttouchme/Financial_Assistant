import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { CurrencySelect } from "@/components/forms/CurrencySelect";

describe("CurrencySelect", () => {
  it("trigger displays the selected currency", () => {
    render(<CurrencySelect value="HUF" onChange={() => {}} />);
    const trigger = screen.getByRole("combobox", { name: /currency/i });
    expect(trigger.textContent).toMatch(/HUF/);
  });

  it("opens with both groups and 31 options", async () => {
    render(<CurrencySelect value="CHF" onChange={() => {}} />);
    fireEvent.click(screen.getByRole("combobox", { name: /currency/i }));
    expect(await screen.findByText("Most used")).toBeInTheDocument();
    expect(screen.getByText("All currencies")).toBeInTheDocument();
    const options = screen.getAllByRole("option");
    expect(options.length).toBe(31);
  });

  it("calls onChange when an option is picked", async () => {
    let last = "";
    render(<CurrencySelect value="CHF" onChange={(v) => (last = v)} />);
    fireEvent.click(screen.getByRole("combobox", { name: /currency/i }));
    const eur = await screen.findByRole("option", { name: /EUR/i });
    fireEvent.click(eur);
    expect(last).toBe("EUR");
  });

  it("rows include symbol + code + name", async () => {
    render(<CurrencySelect value="USD" onChange={() => {}} />);
    fireEvent.click(screen.getByRole("combobox", { name: /currency/i }));
    const usd = await screen.findByRole("option", { name: /USD/i });
    expect(usd.textContent).toContain("$");
    expect(usd.textContent).toContain("USD");
    expect(usd.textContent).toContain("US Dollar");
  });
});
