import { beforeEach, describe, expect, it } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useTheme } from "../useTheme";

beforeEach(() => {
  document.documentElement.className = "";
  window.localStorage.clear();
});

describe("useTheme", () => {
  it("toggles into emerald and adds the .emerald class", () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setTheme("emerald"));
    expect(document.documentElement.classList.contains("emerald")).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(window.localStorage.getItem("fa-theme")).toBe("emerald");
  });

  it("toggles into navy and adds the .navy class", () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setTheme("navy"));
    expect(document.documentElement.classList.contains("navy")).toBe(true);
  });

  it("clears emerald/navy classes when switching to light", () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setTheme("emerald"));
    act(() => result.current.setTheme("light"));
    expect(document.documentElement.classList.contains("emerald")).toBe(false);
    expect(document.documentElement.classList.contains("navy")).toBe(false);
  });

  it("rejects unknown theme strings from storage and falls back to light", () => {
    window.localStorage.setItem("fa-theme", "garbage");
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("light");
  });
});
