import { describe, expect, it, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useFxStatus, useRefreshFx } from "@/hooks/queries/useFx";
import { resetTestState, testState } from "@/tests/handlers";

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe("useFx", () => {
  beforeEach(() => resetTestState());

  it("reads status", async () => {
    const { result } = renderHook(() => useFxStatus(), { wrapper: wrap() });
    await waitFor(() => expect(result.current.data?.is_fresh).toBe(false));
  });

  it("refresh sets latest_date to today", async () => {
    const { result } = renderHook(() => useRefreshFx(), { wrapper: wrap() });
    await act(async () => {
      await result.current.mutateAsync();
    });
    expect(testState.fxStatus.is_fresh).toBe(true);
  });
});
