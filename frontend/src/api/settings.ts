import { apiFetch } from "./client";
import type { BaseCurrencyChangePreview, SettingsRead } from "./types";

export function getSettings(): Promise<SettingsRead> {
  return apiFetch<SettingsRead>("/api/settings");
}

export function updateBaseCurrency(code: string): Promise<SettingsRead> {
  return apiFetch<SettingsRead>("/api/settings/base_currency", {
    method: "PATCH",
    body: JSON.stringify({ base_currency: code }),
  });
}

export function previewBaseCurrencyChange(
  code: string,
): Promise<BaseCurrencyChangePreview> {
  return apiFetch<BaseCurrencyChangePreview>(
    "/api/settings/base_currency/preview",
    {
      method: "POST",
      body: JSON.stringify({ base_currency: code }),
    },
  );
}
