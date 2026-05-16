import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useTheme } from "@/hooks/useTheme";

describe("useTheme", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.classList.remove("dark", "sakura", "cyberpunk");
  });

  it("switches between light and dark and applies the class", () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toMatch(/light|dark/);

    act(() => result.current.setTheme("dark"));
    expect(result.current.theme).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    act(() => result.current.setTheme("light"));
    expect(result.current.theme).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("persists to localStorage", () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setTheme("dark"));
    expect(window.localStorage.getItem("fa-theme")).toBe("dark");
  });
});

describe("useTheme (3-way)", () => {
  beforeEach(() => {
    document.documentElement.classList.remove("dark", "sakura", "cyberpunk");
    window.localStorage.clear();
  });

  it("setTheme('sakura') adds the .sakura class and removes .dark", () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setTheme("dark"));
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    act(() => result.current.setTheme("sakura"));
    expect(document.documentElement.classList.contains("sakura")).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("setTheme('light') removes both classes", () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setTheme("sakura"));
    act(() => result.current.setTheme("light"));
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(document.documentElement.classList.contains("sakura")).toBe(false);
  });

  it("persists sakura to localStorage", () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setTheme("sakura"));
    expect(window.localStorage.getItem("fa-theme")).toBe("sakura");
  });
});

describe("useTheme (cyberpunk)", () => {
  beforeEach(() => {
    document.documentElement.classList.remove("dark", "sakura", "cyberpunk");
    window.localStorage.clear();
  });

  it("supports cyberpunk theme", () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setTheme("cyberpunk"));
    expect(document.documentElement.classList.contains("cyberpunk")).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(document.documentElement.classList.contains("sakura")).toBe(false);
  });

  it("readInitialTheme handles cyberpunk from storage", () => {
    window.localStorage.setItem("fa-theme", "cyberpunk");
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("cyberpunk");
  });
});
