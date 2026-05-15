import { useMemo } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useBudgetsForMonth } from "@/hooks/queries/useBudgets";
import { formatMoney } from "@/lib/money";
import { useSettings } from "@/hooks/queries/useSettings";
import { monthLabel } from "@/lib/date";
import { cn } from "@/lib/utils";

interface Props { month: string }

function toneFor(pct: number): string {
  if (pct >= 100) return "text-destructive";
  if (pct >= 80) return "text-amber-600 dark:text-amber-400";
  return "text-emerald-600 dark:text-emerald-500";
}

function progressColor(pct: number): string {
  if (pct >= 100) return "bg-destructive";
  if (pct >= 80) return "bg-amber-500";
  return "bg-emerald-500";
}

export function BudgetWidget({ month }: Props) {
  const { data, isLoading } = useBudgetsForMonth(month);
  const { data: settings } = useSettings();
  const baseCurrency = settings?.base_currency ?? "CHF";

  const rows = useMemo(() => {
    return (data ?? [])
      .map((b) => {
        const spent = Number(b.spent);
        const limit = Number(b.monthly_limit);
        const pct = limit > 0 ? (spent / limit) * 100 : 0;
        return { ...b, spent, limit, pct };
      })
      .sort((a, b) => b.pct - a.pct);
  }, [data]);

  const totals = rows.reduce(
    (acc, r) => {
      acc.spent += r.spent;
      acc.limit += r.limit;
      return acc;
    },
    { spent: 0, limit: 0 },
  );
  const totalPct = totals.limit > 0 ? (totals.spent / totals.limit) * 100 : 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle>Budgets · {monthLabel(month)}</CardTitle>
        <Link
          to="/budgets"
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          edit on /budgets
        </Link>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <Skeleton className="h-16 w-full" />
        ) : rows.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">
            No budgets set for this month. Set one on /budgets.
          </p>
        ) : (
          <>
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-lg font-semibold tabular-nums">
                  {formatMoney(totals.spent, baseCurrency)}
                </span>
                <span className="text-muted-foreground text-sm">
                  / {formatMoney(totals.limit, baseCurrency)}
                </span>
                <span
                  className={cn("ml-auto text-sm font-medium", toneFor(totalPct))}
                >
                  {totalPct.toFixed(0)}%
                </span>
              </div>
              <Progress
                value={Math.min(100, totalPct)}
                indicatorClassName={progressColor(totalPct)}
              />
              <div className="text-xs text-muted-foreground">
                {formatMoney(Math.max(0, totals.limit - totals.spent), baseCurrency)} remaining
              </div>
            </div>

            <ul className="divide-y -mx-2">
              {rows.map((r) => (
                <li
                  key={r.category_id}
                  className="flex items-center gap-3 py-2 px-2"
                >
                  <div className="w-32 truncate font-medium">{r.category_name}</div>
                  <div className="flex-1">
                    <Progress
                      value={Math.min(100, r.pct)}
                      indicatorClassName={progressColor(r.pct)}
                    />
                  </div>
                  <div className="w-32 text-right tabular-nums text-sm">
                    {formatMoney(r.spent, baseCurrency)}
                    <span className="text-muted-foreground"> / {formatMoney(r.limit, baseCurrency)}</span>
                  </div>
                  <div
                    className={cn(
                      "w-12 text-right text-sm font-medium",
                      toneFor(r.pct),
                    )}
                  >
                    {r.pct.toFixed(0)}%
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </CardContent>
    </Card>
  );
}
