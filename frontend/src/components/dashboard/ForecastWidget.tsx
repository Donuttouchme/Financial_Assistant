import { Link, useSearchParams } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ForecastChart } from "@/components/forecast/ForecastChart";
import { CategoryFilter } from "@/components/forecast/CategoryFilter";
import { ColdStartHint } from "@/components/forecast/ColdStartHint";
import { useCategories } from "@/hooks/queries/useCategories";
import { useDailyCumulative } from "@/hooks/queries/useForecast";

interface Props { month: string }

export function ForecastWidget({ month }: Props) {
  const [search] = useSearchParams();
  const categoryId = (() => {
    const raw = search.get("category");
    if (!raw || raw === "all") return undefined;
    const n = Number(raw);
    return Number.isFinite(n) ? n : undefined;
  })();

  const { data: cats } = useCategories();
  const { data, isLoading } = useDailyCumulative({ month, categoryId });

  const linkQuery = new URLSearchParams(search);
  if (!linkQuery.get("horizon")) linkQuery.set("horizon", "1m");

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle>This month — forecast</CardTitle>
        <div className="flex items-center gap-3">
          {cats && <CategoryFilter categories={cats} />}
          <Link
            to={`/forecast?${linkQuery.toString()}`}
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            See full forecast <ArrowUpRight className="h-4 w-4" />
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading || !data ? (
          <Skeleton className="h-72 w-full" />
        ) : (
          <>
            <ForecastChart mode="daily" daily={data} />
            {!data.forecast_available && <ColdStartHint reason="no-forecast" />}
          </>
        )}
      </CardContent>
    </Card>
  );
}
