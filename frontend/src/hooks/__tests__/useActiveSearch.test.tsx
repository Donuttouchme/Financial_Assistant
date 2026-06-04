import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useActiveSearch } from "@/hooks/useActiveSearch";

function wrap(initial: string) {
  return ({ children }: { children: React.ReactNode }) => (
    <MemoryRouter initialEntries={[initial]}>{children}</MemoryRouter>
  );
}

describe("useActiveSearch", () => {
  it("returns the trimmed term for >= 2 chars", () => {
    const { result } = renderHook(() => useActiveSearch(), {
      wrapper: wrap("/transactions?q=%20ab%20"),
    });
    expect(result.current).toBe("ab");
  });

  it("returns null below 2 chars", () => {
    const { result } = renderHook(() => useActiveSearch(), {
      wrapper: wrap("/transactions?q=a"),
    });
    expect(result.current).toBeNull();
  });

  it("returns null when q is missing", () => {
    const { result } = renderHook(() => useActiveSearch(), {
      wrapper: wrap("/transactions"),
    });
    expect(result.current).toBeNull();
  });
});
