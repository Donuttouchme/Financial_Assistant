import { describe, expect, it } from "vitest";
import { CURRENCY_SYMBOLS, formatMoney, parseMoneyInput } from "@/lib/money";

describe("formatMoney", () => {
  it("formats CHF with Swiss locale", () => {
    // ICU uses U+00A0 (non-breaking space) between "CHF" and the number.
    expect(formatMoney("12345.67", "CHF")).toBe("CHF 12’345.67");
  });

  it("formats HUF with no decimals", () => {
    const formatted = formatMoney(5000, "HUF");
    expect(formatted.replace(/[  ]/g, " ")).toBe("5 000 Ft");
  });

  it("formats USD with en-US locale", () => {
    expect(formatMoney(1234.56, "USD")).toBe("$1,234.56");
  });

  it("falls back to plain number when currency is unknown", () => {
    expect(formatMoney(100, "XYZ")).toBe("100.00 XYZ");
  });
});

describe("parseMoneyInput", () => {
  it("strips thousand separators and apostrophes", () => {
    expect(parseMoneyInput("12'345.67")).toBe("12345.67");
    expect(parseMoneyInput("12’345.67")).toBe("12345.67");
    expect(parseMoneyInput("12 345.67")).toBe("12345.67");
  });

  it("preserves leading minus", () => {
    expect(parseMoneyInput("-50.25")).toBe("-50.25");
  });

  it("throws on non-numeric input", () => {
    expect(() => parseMoneyInput("abc")).toThrow();
  });
});

describe("CURRENCY_SYMBOLS", () => {
  it("has known symbols for major currencies", () => {
    expect(CURRENCY_SYMBOLS["USD"]).toBe("$");
    expect(CURRENCY_SYMBOLS["EUR"]).toBe("€");
    expect(CURRENCY_SYMBOLS["GBP"]).toBe("£");
    expect(CURRENCY_SYMBOLS["JPY"]).toBe("¥");
    expect(CURRENCY_SYMBOLS["HUF"]).toBe("Ft");
  });
});
