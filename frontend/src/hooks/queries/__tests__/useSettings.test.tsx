import { describe, expect, it, beforeEach } from "vitest";
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
});
