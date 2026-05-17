import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { format } from "date-fns";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ForecastChart } from "@/components/forecast/ForecastChart";
import { CategoryFilter } from "@/components/forecast/CategoryFilter";
import { HorizonPicker } from "@/components/forecast/HorizonPicker";
import { ForecastModeToggle } from "@/components/forecast/ForecastModeToggle";
import { ForecastEmptyState } from "@/components/forecast/ColdStartHint";
import { useCategories } from "@/hooks/queries/useCategories";
import {
  useDailyCumulative, useMonthlyBuckets,
} from "@/hooks/queries/useForecast";
import type { ForecastHorizon, ForecastMode } from "@/api/types";

const VALID_HORIZONS: ForecastHorizon[] = ["1m", "3m", "6m", "1y", "2y"];

export default function ForecastPage() {
  const [search] = useSearchParams();
  const horizon = (() => {
    const v = search.get("horizon") as ForecastHorizon | null;
    return v && VALID_HORIZONS.includes(v) ? v : "6m";
  })();
  const mode = (search.get("mode") as ForecastMode) || "centered";
  const categoryId = (() => {
    const raw = search.get("category");
    if (!raw || raw === "all") return undefined;
    const n = Number(raw);
    return Number.isFinite(n) ? n : undefined;
  })();

  const isDailyMode = horizon === "1m";
  const currentMonth = useMemo(() => format(new Date(), "yyyy-MM"), []);

  const daily = useDailyCumulative({
    month: currentMonth,
    categoryId,
  });
  const monthly = useMonthlyBuckets({
    horizon, mode, categoryId,
  });

  const { data: cats } = useCategories();

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Forecast</h2>

      <Card>
        <CardHeader className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <HorizonPicker />
            {!isDailyMode && <ForecastModeToggle />}
            <div className="ml-auto">
              {cats && <CategoryFilter categories={cats} />}
            </div>
          </div>
          <CardTitle className="text-base font-normal text-muted-foreground">
            {isDailyMode
              ? "This month, day-by-day"
              : `${horizon} ${mode === "forward" ? "(forecast only)" : "(centered on today)"}`}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isDailyMode ? (
            daily.isLoading || !daily.data ? (
              <Skeleton className="h-72 w-full" />
            ) : !daily.data.forecast_available ? (
              <ForecastEmptyState />
            ) : (
              <ForecastChart mode="daily" daily={daily.data} />
            )
          ) : (
            monthly.isLoading || !monthly.data ? (
              <Skeleton className="h-72 w-full" />
            ) : !monthly.data.forecast_available ? (
              <ForecastEmptyState />
            ) : (
              <ForecastChart mode="monthly" monthly={monthly.data} />
            )
          )}
        </CardContent>
      </Card>
    </div>
  );
}
