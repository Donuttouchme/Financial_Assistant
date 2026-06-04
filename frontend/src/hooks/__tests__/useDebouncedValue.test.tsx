import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";

afterEach(() => vi.useRealTimers());

describe("useDebouncedValue", () => {
  it("returns the latest value only after the delay elapses", () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(
      ({ v }) => useDebouncedValue(v, 300),
      { initialProps: { v: "a" } },
    );
    expect(result.current).toBe("a");

    rerender({ v: "ab" });
    expect(result.current).toBe("a"); // not yet — timer pending

    act(() => vi.advanceTimersByTime(300));
    expect(result.current).toBe("ab");
  });
});
