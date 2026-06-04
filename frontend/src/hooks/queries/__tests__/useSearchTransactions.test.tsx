import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSearchTransactions } from "@/hooks/queries/useTransactions";
import { resetTestState, testState } from "@/tests/handlers";

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

beforeEach(() => {
  resetTestState();
  testState.categories.push({
    id: 1, name: "Food", kind: "expense",
    target_amount: null, target_date: null, created_at: "",
  });
  testState.transactions.push({
    id: 1, user_id: 1, amount: "10", date: "2026-01-05", category_id: 1,
    description: "lunch out", is_recurring: false, currency: "CHF",
    base_amount: "10", created_at: "", updated_at: "",
  });
});

describe("useSearchTransactions", () => {
  it("fetches results matching the term", async () => {
    const { result } = renderHook(() => useSearchTransactions("lun"), {
      wrapper: wrap(),
    });
    await waitFor(() => expect(result.current.data?.length).toBe(1));
    expect(result.current.data?.[0].description).toBe("lunch out");
  });

  it("does not fetch when disabled", () => {
    const { result } = renderHook(
      () => useSearchTransactions("lun", { enabled: false }),
      { wrapper: wrap() },
    );
    expect(result.current.fetchStatus).toBe("idle");
  });
});
