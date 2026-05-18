import { describe, expect, it, beforeEach, vi } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useRecurring,
  useUpdateRecurring,
  useDeleteRecurring,
} from "@/hooks/queries/useRecurring";
import { resetTestState, testState } from "@/tests/handlers";
import type { RecurringSchedule } from "@/api/types";

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

function seedSchedule(): RecurringSchedule {
  const sched: RecurringSchedule = {
    id: 1,
    transaction_id: 100,
    amount: "-25.00",
    category_id: 1,
    description: "Netflix",
    currency: "CHF",
    start_date: "2026-01-01",
    next_occurrence_date: "2026-06-01",
    frequency: "monthly",
  };
  testState.recurringSchedules.push(sched);
  testState.nextScheduleId = 2;
  return sched;
}

describe("useRecurring", () => {
  beforeEach(() => resetTestState());

  it("returns the list of schedules from MSW", async () => {
    seedSchedule();
    const { result } = renderHook(() => useRecurring(), { wrapper: wrap() });
    await waitFor(() => expect(result.current.data).toHaveLength(1));
    expect(result.current.data?.[0].description).toBe("Netflix");
  });

  it("useUpdateRecurring invalidates recurring, transactions, forecast", async () => {
    seedSchedule();
    const { wrapper, spy } = wrapWithSpy();
    const { result } = renderHook(() => useUpdateRecurring(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({
        id: 1,
        body: { amount: "-30.00" },
      });
    });
    expect(spy).toHaveBeenCalledTimes(3);
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["recurring"] }),
    );
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["transactions"] }),
    );
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["forecast"] }),
    );
    expect(testState.recurringSchedules[0].amount).toBe("-30.00");
  });

  it("useDeleteRecurring invalidates recurring, transactions, forecast", async () => {
    seedSchedule();
    const { wrapper, spy } = wrapWithSpy();
    const { result } = renderHook(() => useDeleteRecurring(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync(1);
    });
    expect(spy).toHaveBeenCalledTimes(3);
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["recurring"] }),
    );
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["transactions"] }),
    );
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["forecast"] }),
    );
    expect(testState.recurringSchedules).toHaveLength(0);
  });
});
