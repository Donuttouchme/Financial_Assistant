import { apiFetch } from "./client";
import type { FxRefreshResponse, FxStatusRead } from "./types";

export function getFxStatus(): Promise<FxStatusRead> {
  return apiFetch<FxStatusRead>("/api/fx/status");
}

export function refreshFx(): Promise<FxRefreshResponse> {
  return apiFetch<FxRefreshResponse>("/api/fx/refresh", { method: "POST" });
}
