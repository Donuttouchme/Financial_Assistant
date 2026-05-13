import { apiFetch } from "./client";
import type { ImportPreset, ImportPresetCreatePayload } from "./types";

export function listImportPresets(): Promise<ImportPreset[]> {
  return apiFetch<ImportPreset[]>("/api/import-presets");
}

export function createImportPreset(
  p: ImportPresetCreatePayload,
): Promise<ImportPreset> {
  return apiFetch<ImportPreset>("/api/import-presets", {
    method: "POST",
    body: JSON.stringify(p),
  });
}

export function updateImportPreset(
  id: number,
  p: ImportPresetCreatePayload,
): Promise<ImportPreset> {
  return apiFetch<ImportPreset>(`/api/import-presets/${id}`, {
    method: "PUT",
    body: JSON.stringify(p),
  });
}

export function deleteImportPreset(id: number): Promise<void> {
  return apiFetch<void>(`/api/import-presets/${id}`, { method: "DELETE" });
}
