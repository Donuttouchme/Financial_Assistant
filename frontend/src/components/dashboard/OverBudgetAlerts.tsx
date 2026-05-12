import { AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useBudgetsForMonth } from "@/hooks/queries/useBudgets";
import { formatChf } from "@/lib/currency";

interface Props { month: string }

export function OverBudgetAlerts({ month }: Props) {
  const { data, isLoading } = useBudgetsForMonth(month);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-destructive" />
          Over budget
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-16 w-full" />
        ) : (() => {
          const over = (data ?? []).filter((b) => b.over_budget);
          if (over.length === 0) {
            return (
              <p className="text-sm text-muted-foreground italic">
                Nothing over budget this month. Nice.
              </p>
            );
          }
          return (
            <ul className="divide-y">
              {over.map((b) => (
                <li
                  key={b.category_id}
                  className="flex items-center justify-between py-2"
                >
                  <span>{b.category_name}</span>
                  <span className="text-right">
                    <span className="tabular-nums">
                      {formatChf(b.spent)}
                    </span>
                    <span className="text-muted-foreground">
                      {" / "}
                      {formatChf(b.monthly_limit)}
                    </span>
                    <span className="text-destructive ml-2 font-medium">
                      +{formatChf(b.overage)}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          );
        })()}
      </CardContent>
    </Card>
  );
}
