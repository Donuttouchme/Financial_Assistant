import { apiFetchBlob } from "./client";

export function downloadTransactionsCsv(month?: string): Promise<Blob> {
  const qs = month ? `?month=${encodeURIComponent(month)}` : "";
  return apiFetchBlob(`/api/export/csv${qs}`);
}
