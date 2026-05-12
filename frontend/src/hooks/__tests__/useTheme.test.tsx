import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useTheme } from "@/hooks/useTheme";

describe("useTheme", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  it("toggles between light and dark and applies the class", () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toMatch(/light|dark/);

    const initial = result.current.theme;
    act(() => result.current.toggle());
    expect(result.current.theme).not.toBe(initial);

    if (result.current.theme === "dark") {
      expect(document.documentElement.classList.contains("dark")).toBe(true);
    } else {
      expect(document.documentElement.classList.contains("dark")).toBe(false);
    }
  });

  it("persists to localStorage", () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setTheme("dark"));
    expect(window.localStorage.getItem("fa-theme")).toBe("dark");
  });
});
