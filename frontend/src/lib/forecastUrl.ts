import type { ForecastHorizon, ForecastMode } from "@/api/types";

const HORIZONS: readonly ForecastHorizon[] = ["1m", "3m", "6m", "1y", "2y"];
const MODES: readonly ForecastMode[] = ["centered", "forward"];

export function parseHorizon(raw: string | null | undefined): ForecastHorizon {
  return HORIZONS.includes(raw as ForecastHorizon) ? (raw as ForecastHorizon) : "6m";
}

export function parseMode(raw: string | null | undefined): ForecastMode {
  return MODES.includes(raw as ForecastMode) ? (raw as ForecastMode) : "centered";
}

export function parseCategoryId(raw: string | null | undefined): number | undefined {
  if (!raw) return undefined;
  const n = Number(raw);
  return Number.isInteger(n) && n > 0 ? n : undefined;
}
