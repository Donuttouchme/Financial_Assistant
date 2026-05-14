import { apiFetch } from "./client";

export async function postHeartbeat(): Promise<void> {
  await apiFetch("/api/heartbeat", { method: "POST" });
}
