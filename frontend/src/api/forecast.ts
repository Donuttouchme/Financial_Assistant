import { apiFetch } from "./client";
import type {
  DailyCumulativeResponse,
  ForecastHorizon,
  ForecastMode,
  MonthlyBucketsResponse,
} from "./types";

export function getDailyCumulative(params: {
  month: string;
  categoryId?: number;
}): Promise<DailyCumulativeResponse> {
  const q = new URLSearchParams({ month: params.month });
  if (params.categoryId !== undefined) {
    q.set("category_id", String(params.categoryId));
  }
  return apiFetch<DailyCumulativeResponse>(
    `/api/forecast/daily-cumulative?${q.toString()}`,
  );
}

export function getMonthlyBuckets(params: {
  horizon: ForecastHorizon;
  mode: ForecastMode;
  categoryId?: number;
}): Promise<MonthlyBucketsResponse> {
  const q = new URLSearchParams({
    horizon: params.horizon,
    mode: params.mode,
  });
  if (params.categoryId !== undefined) {
    q.set("category_id", String(params.categoryId));
  }
  return apiFetch<MonthlyBucketsResponse>(
    `/api/forecast/monthly-buckets?${q.toString()}`,
  );
}
