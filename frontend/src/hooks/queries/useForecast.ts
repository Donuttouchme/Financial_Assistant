import { useQuery } from "@tanstack/react-query";

import { getDailyCumulative, getMonthlyBuckets } from "@/api/forecast";
import type { ForecastHorizon, ForecastMode } from "@/api/types";

export function useDailyCumulative(params: {
  month: string;
  categoryId?: number;
}) {
  return useQuery({
    queryKey: ["forecast", "daily-cumulative", params.month, params.categoryId ?? null],
    queryFn: () => getDailyCumulative(params),
    staleTime: 60_000,
  });
}

export function useMonthlyBuckets(params: {
  horizon: ForecastHorizon;
  mode: ForecastMode;
  categoryId?: number;
}) {
  return useQuery({
    queryKey: ["forecast", "monthly-buckets", params.horizon, params.mode, params.categoryId ?? null],
    queryFn: () => getMonthlyBuckets(params),
    staleTime: 60_000,
  });
}
