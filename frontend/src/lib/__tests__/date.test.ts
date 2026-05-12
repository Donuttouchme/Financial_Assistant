import { describe, it, expect } from "vitest";
import { currentMonth, monthLabel, monthOptions } from "@/lib/date";

describe("currentMonth", () => {
  it("returns YYYY-MM for a given Date", () => {
    expect(currentMonth(new Date("2026-05-12T10:00:00Z"))).toBe("2026-05");
  });

  it("zero-pads single-digit months", () => {
    expect(currentMonth(new Date("2026-01-01T10:00:00Z"))).toBe("2026-01");
  });
});

describe("monthLabel", () => {
  it("renders YYYY-MM as a long label", () => {
    expect(monthLabel("2026-05")).toBe("May 2026");
  });
});

describe("monthOptions", () => {
  it("returns 24 months ending at the given month, descending", () => {
    const list = monthOptions("2026-05");
    expect(list).toHaveLength(24);
    expect(list[0]).toEqual({ value: "2026-05", label: "May 2026" });
    expect(list[1].value).toBe("2026-04");
    expect(list[23].value).toBe("2024-06");
  });
});
