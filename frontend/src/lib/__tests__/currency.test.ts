import { describe, it, expect } from "vitest";
import { formatChf, parseChfInput } from "@/lib/currency";

// Node ICU produces non-breaking space (U+00A0) between "CHF" and the number,
// and right single quotation mark (U+2019) as the thousands separator.
describe("formatChf", () => {
  it("formats a positive amount", () => {
    expect(formatChf("12345.67")).toBe("CHF 12’345.67");
  });

  it("formats zero", () => {
    expect(formatChf("0")).toBe("CHF 0.00");
  });

  it("accepts number input", () => {
    expect(formatChf(50)).toBe("CHF 50.00");
  });
});

describe("parseChfInput", () => {
  it("strips spaces and accepts apostrophes", () => {
    expect(parseChfInput("12’345.67")).toBe("12345.67");
    expect(parseChfInput("1 234.50")).toBe("1234.50");
  });

  it("returns the string as-is when already clean", () => {
    expect(parseChfInput("12.34")).toBe("12.34");
  });

  it("rejects non-numeric", () => {
    expect(() => parseChfInput("abc")).toThrow(/numeric/);
  });
});
