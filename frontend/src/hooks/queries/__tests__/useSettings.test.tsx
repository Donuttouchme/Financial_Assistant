import { describe, expect, it, beforeEach, vi } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSettings, useUpdateBaseCurrency } from "@/hooks/queries/useSettings";
import { resetTestState, testState } from "@/tests/handlers";

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

function wrapWithSpy() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const spy = vi.spyOn(qc, "invalidateQueries");
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return { wrapper, spy };
}

describe("useSettings", () => {
  beforeEach(() => resetTestState());

  it("reads base currency", async () => {
    const { result } = renderHook(() => useSettings(), { wrapper: wrap() });
    await waitFor(() => expect(result.current.data).toEqual({ base_currency: "CHF" }));
  });

  it("updates base currency", async () => {
    const { result } = renderHook(() => useUpdateBaseCurrency(), { wrapper: wrap() });
    await act(async () => {
      await result.current.mutateAsync("HUF");
    });
    expect(testState.settings.base_currency).toBe("HUF");
  });

  it("invalidates the forecast cache after base currency update", async () => {
    const { wrapper, spy } = wrapWithSpy();
    const { result } = renderHook(() => useUpdateBaseCurrency(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync("HUF");
    });
    expect(spy).toHaveBeenCalledTimes(5);
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["forecast"] }));
  });
});
