import { describe, it, expect } from "vitest";
import { parseHorizon, parseMode, parseCategoryId } from "../forecastUrl";

describe("forecastUrl validators", () => {
  it("parseHorizon defaults to 6m on invalid input", () => {
    expect(parseHorizon(null)).toBe("6m");
    expect(parseHorizon(undefined)).toBe("6m");
    expect(parseHorizon("")).toBe("6m");
    expect(parseHorizon("garbage")).toBe("6m");
  });
  it("parseHorizon passes through valid horizons", () => {
    for (const h of ["1m", "3m", "6m", "1y", "2y"] as const) {
      expect(parseHorizon(h)).toBe(h);
    }
  });
  it("parseMode defaults to centered on invalid input", () => {
    expect(parseMode(null)).toBe("centered");
    expect(parseMode("sideways")).toBe("centered");
  });
  it("parseMode passes through valid modes", () => {
    expect(parseMode("centered")).toBe("centered");
    expect(parseMode("forward")).toBe("forward");
  });
  it("parseCategoryId rejects garbage and non-positive integers", () => {
    expect(parseCategoryId(null)).toBeUndefined();
    expect(parseCategoryId(undefined)).toBeUndefined();
    expect(parseCategoryId("")).toBeUndefined();
    expect(parseCategoryId("banana")).toBeUndefined();
    expect(parseCategoryId("-1")).toBeUndefined();
    expect(parseCategoryId("0")).toBeUndefined();
    expect(parseCategoryId("1.5")).toBeUndefined();
  });
  it("parseCategoryId accepts positive integers", () => {
    expect(parseCategoryId("42")).toBe(42);
    expect(parseCategoryId("1")).toBe(1);
  });
});
