import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { server } from "../../tests/setup";
import { http, HttpResponse } from "msw";
import { useHeartbeat } from "../useHeartbeat";

describe("useHeartbeat", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("posts /api/heartbeat once per interval while mounted", async () => {
    const calls: number = await new Promise((resolve) => {
      let n = 0;
      server.use(
        http.post("/api/heartbeat", () => {
          n += 1;
          return HttpResponse.json({ ok: true });
        }),
      );
      renderHook(() => useHeartbeat(1000));
      // first immediate tick + two intervals
      Promise.resolve().then(async () => {
        await vi.advanceTimersByTimeAsync(0);
        await vi.advanceTimersByTimeAsync(1000);
        await vi.advanceTimersByTimeAsync(1000);
        resolve(n);
      });
    });
    expect(calls).toBeGreaterThanOrEqual(2);
  });

  it("does not post after unmount", async () => {
    let n = 0;
    server.use(
      http.post("/api/heartbeat", () => {
        n += 1;
        return HttpResponse.json({ ok: true });
      }),
    );
    const { unmount } = renderHook(() => useHeartbeat(1000));
    await vi.advanceTimersByTimeAsync(0);
    const afterMount = n;
    unmount();
    await vi.advanceTimersByTimeAsync(5000);
    expect(n).toBe(afterMount);
  });
});
