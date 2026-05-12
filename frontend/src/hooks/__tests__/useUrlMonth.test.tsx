import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useUrlMonth } from "@/hooks/useUrlMonth";

function wrapper({ children, initial }: { children: React.ReactNode; initial: string }) {
  return <MemoryRouter initialEntries={[initial]}>{children}</MemoryRouter>;
}

describe("useUrlMonth", () => {
  it("reads ?month from URL", () => {
    const { result } = renderHook(() => useUrlMonth(), {
      wrapper: ({ children }) => wrapper({ children, initial: "/dashboard?month=2026-03" }),
    });
    expect(result.current.month).toBe("2026-03");
  });

  it("falls back to current month when param missing", () => {
    const { result } = renderHook(() => useUrlMonth(), {
      wrapper: ({ children }) => wrapper({ children, initial: "/dashboard" }),
    });
    expect(result.current.month).toMatch(/^\d{4}-\d{2}$/);
  });

  it("setMonth pushes ?month into URL", () => {
    const { result } = renderHook(() => useUrlMonth(), {
      wrapper: ({ children }) => wrapper({ children, initial: "/dashboard" }),
    });
    act(() => result.current.setMonth("2026-01"));
    expect(result.current.month).toBe("2026-01");
  });
});
