import { useMemo } from "react";
import { Pie, PieChart, Cell } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ChartContainer,
  ChartTooltip, ChartTooltipContent,
} from "@/components/ui/chart";
import { useTransactions } from "@/hooks/queries/useTransactions";
import { useCategories } from "@/hooks/queries/useCategories";
import { formatMoney } from "@/lib/money";
import { useBaseCurrency } from "@/hooks/queries/useSettings";

interface Props { month: string }

interface Slice {
  category: string;
  amount: number;
  fill: string;
}

const PALETTE = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
];

export function CategoryDonut({ month }: Props) {
  const { data: txs, isLoading: txsLoading } = useTransactions({ month });
  const { data: cats, isLoading: catsLoading } = useCategories();
  const baseCurrency = useBaseCurrency();

  const slices: Slice[] = useMemo(() => {
    if (!txs || !cats) return [];
    const expense = new Map(
      cats.filter((c) => c.kind === "expense").map((c) => [c.id, c.name]),
    );
    const totals = new Map<number, number>();
    for (const t of txs) {
      if (!expense.has(t.category_id)) continue;
      if (t.base_amount === null) continue;
      totals.set(t.category_id, (totals.get(t.category_id) ?? 0) + Number(t.base_amount));
    }
    return [...totals.entries()]
      .sort(([, a], [, b]) => b - a)
      .map(([id, amount], i) => ({
        category: expense.get(id) ?? `#${id}`,
        amount,
        fill: PALETTE[i % PALETTE.length],
      }));
  }, [txs, cats]);

  const total = slices.reduce((s, x) => s + x.amount, 0);

  const config = Object.fromEntries(
    slices.map((s, i) => [
      s.category,
      { label: s.category, color: PALETTE[i % PALETTE.length] },
    ]),
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Expense by category</CardTitle>
      </CardHeader>
      <CardContent>
        {txsLoading || catsLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : slices.length === 0 ? (
          <p className="text-sm text-muted-foreground italic py-12 text-center">
            No expense transactions in this month.
          </p>
        ) : (
          <>
            <ChartContainer config={config} className="mx-auto aspect-square h-64">
              <PieChart>
                <ChartTooltip
                  cursor={false}
                  content={
                    <ChartTooltipContent
                      hideLabel
                      formatter={(value, _name, item) => {
                        const v = Number(value);
                        const pct = total > 0 ? (v / total) * 100 : 0;
                        return [
                          `${formatMoney(v, baseCurrency)} (${pct.toFixed(0)}%)`,
                          item.payload.category,
                        ];
                      }}
                    />
                  }
                />
                <Pie
                  data={slices}
                  dataKey="amount"
                  nameKey="category"
                  innerRadius={55}
                  strokeWidth={2}
                >
                  {slices.map((s) => (
                    <Cell key={s.category} fill={s.fill} />
                  ))}
                </Pie>
              </PieChart>
            </ChartContainer>
            <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 pt-3 text-xs">
              {slices.map((s) => {
                const pct = total > 0 ? (s.amount / total) * 100 : 0;
                return (
                  <div key={s.category} className="flex items-center gap-1.5">
                    <span
                      className="inline-block h-2 w-2 rounded-[2px]"
                      style={{ backgroundColor: s.fill }}
                      aria-hidden
                    />
                    <span>{s.category}</span>
                    <span className="text-muted-foreground">({pct.toFixed(0)}%)</span>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
