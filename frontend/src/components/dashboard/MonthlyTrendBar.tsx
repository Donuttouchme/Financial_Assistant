import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { useQueries } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ChartContainer, ChartTooltip, ChartTooltipContent,
} from "@/components/ui/chart";
import { listTransactions } from "@/api/transactions";
import { useCategories } from "@/hooks/queries/useCategories";
import { format, parse, subMonths } from "date-fns";
import { formatMoney } from "@/lib/money";
import { useSettings } from "@/hooks/queries/useSettings";

interface Props { month: string }

function lastSixMonths(end: string): string[] {
  const endDate = parse(end, "yyyy-MM", new Date());
  const out: string[] = [];
  for (let i = 5; i >= 0; i--) {
    out.push(format(subMonths(endDate, i), "yyyy-MM"));
  }
  return out;
}

export function MonthlyTrendBar({ month }: Props) {
  const months = useMemo(() => lastSixMonths(month), [month]);
  const queries = useQueries({
    queries: months.map((m) => ({
      queryKey: ["transactions", m, null],
      queryFn: () => listTransactions({ month: m }),
    })),
  });
  const { data: cats, isLoading: catsLoading } = useCategories();
  const { data: settings } = useSettings();
  const baseCurrency = settings?.base_currency ?? "CHF";

  const isLoading = catsLoading || queries.some((q) => q.isLoading);

  const data = useMemo(() => {
    if (isLoading || !cats) return [];
    const expense = new Set(
      cats.filter((c) => c.kind === "expense").map((c) => c.id),
    );
    return months.map((m, i) => {
      const txs = queries[i].data ?? [];
      const total = txs
        .filter((t) => expense.has(t.category_id))
        .reduce((s, t) => s + (t.base_amount === null ? 0 : Number(t.base_amount)), 0);
      return {
        month: format(parse(m, "yyyy-MM", new Date()), "MMM"),
        total,
      };
    });
  }, [isLoading, cats, months, queries]);

  const config = {
    total: { label: "Expense", color: "hsl(var(--chart-1))" },
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Last 6 months — expense</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <ChartContainer config={config} className="h-64 w-full">
            <BarChart data={data}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis dataKey="month" tickLine={false} axisLine={false} />
              <YAxis tickLine={false} axisLine={false} width={50} />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    formatter={(value) => formatMoney(Number(value), baseCurrency)}
                  />
                }
              />
              <Bar dataKey="total" fill="var(--color-total)" radius={4} />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
