import { useEffect } from "react";
import { postHeartbeat } from "@/api/heartbeat";

const DEFAULT_INTERVAL_MS = 5 * 60 * 1000;

/**
 * Sends a POST /api/heartbeat at startup and every `intervalMs` thereafter
 * while the component is mounted. The backend uses this to know a tab is
 * still open so the idle watchdog doesn't shut it down.
 */
export function useHeartbeat(intervalMs: number = DEFAULT_INTERVAL_MS) {
  useEffect(() => {
    // Fire-and-forget — heartbeat failures are not user-visible.
    void postHeartbeat();
    const handle = setInterval(() => {
      void postHeartbeat();
    }, intervalMs);
    return () => clearInterval(handle);
  }, [intervalMs]);
}
