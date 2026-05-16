import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useTransactions } from "@/hooks/queries/useTransactions";
import { useCategories } from "@/hooks/queries/useCategories";
import { formatMoney } from "@/lib/money";
import { useBaseCurrency } from "@/hooks/queries/useSettings";
import { cn } from "@/lib/utils";

interface Props { month: string }

interface Stat {
  label: string;
  value: string;
  hint?: string;
  emphasis?: "positive" | "negative" | "neutral";
}

function StatCard({ label, value, hint, emphasis = "neutral" }: Stat) {
  return (
    <Card>
      <CardContent className="py-4">
        <div className="text-sm text-muted-foreground">{label}</div>
        <div
          className={cn(
            "text-2xl font-semibold tabular-nums",
            emphasis === "positive" && "text-emerald-600 dark:text-emerald-500",
            emphasis === "negative" && "text-destructive",
          )}
        >
          {value}
        </div>
        {hint && <div className="text-xs text-muted-foreground mt-1">{hint}</div>}
      </CardContent>
    </Card>
  );
}

export function KpiRow({ month }: Props) {
  const { data: txs, isLoading: txsLoading } = useTransactions({ month });
  const { data: cats, isLoading: catsLoading } = useCategories();
  const baseCurrency = useBaseCurrency();

  if (txsLoading || catsLoading) {
    return (
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24" />)}
      </div>
    );
  }

  const catKindById = new Map((cats ?? []).map((c) => [c.id, c.kind]));
  const sums = (txs ?? []).reduce(
    (acc, t) => {
      const kind = catKindById.get(t.category_id);
      const n = t.base_amount === null ? 0 : Number(t.base_amount);
      if (kind === "income") acc.income += n;
      else if (kind === "expense") acc.expense += n;
      else if (kind === "savings") acc.saved += n;  // can be negative for withdrawals
      return acc;
    },
    { income: 0, expense: 0, saved: 0 },
  );
  const net = sums.income - sums.expense - sums.saved;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard label="Income"  value={formatMoney(sums.income,  baseCurrency)} emphasis="positive" />
      <StatCard label="Expense" value={formatMoney(sums.expense, baseCurrency)} emphasis="negative" />
      <StatCard label="Net"     value={formatMoney(net,          baseCurrency)} emphasis={net >= 0 ? "positive" : "negative"} />
      <StatCard label="Saved"   value={formatMoney(sums.saved,   baseCurrency)} emphasis={sums.saved >= 0 ? "positive" : "negative"} />
    </div>
  );
}
