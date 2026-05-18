import { describe, expect, it, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useDeleteCategory } from "@/hooks/queries/useCategories";
import { resetTestState, testState } from "@/tests/handlers";

function wrapWithSpy() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const spy = vi.spyOn(qc, "invalidateQueries");
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return { wrapper, spy };
}

describe("useCategories", () => {
  beforeEach(() => resetTestState());

  it("invalidates the forecast cache after category delete", async () => {
    testState.categories.push({
      id: 1,
      name: "Groceries",
      kind: "expense",
      target_amount: null,
      target_date: null,
      created_at: new Date().toISOString(),
    });
    testState.nextCatId = 2;

    const { wrapper, spy } = wrapWithSpy();
    const { result } = renderHook(() => useDeleteCategory(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync(1);
    });
    expect(spy).toHaveBeenCalledTimes(4);
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["forecast"] }));
  });
});
