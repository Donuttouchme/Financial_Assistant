import { apiFetch } from "./client";
import type { RecurringSchedule, RecurringUpdate } from "./types";

export function listRecurring(): Promise<RecurringSchedule[]> {
  return apiFetch<RecurringSchedule[]>("/api/recurring");
}

export function getRecurring(id: number): Promise<RecurringSchedule> {
  return apiFetch<RecurringSchedule>(`/api/recurring/${id}`);
}

export function updateRecurring(
  id: number,
  payload: RecurringUpdate,
): Promise<RecurringSchedule> {
  return apiFetch<RecurringSchedule>(`/api/recurring/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteRecurring(id: number): Promise<void> {
  return apiFetch<void>(`/api/recurring/${id}`, { method: "DELETE" });
}
