import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useTransactions } from "@/hooks/queries/useTransactions";
import { useCategories } from "@/hooks/queries/useCategories";
import { formatMoney } from "@/lib/money";
import { useBaseCurrency } from "@/hooks/queries/useSettings";

interface Props { month: string; limit?: number }

export function RecentTransactions({ month, limit = 5 }: Props) {
  const { data: txs, isLoading: txsLoading } = useTransactions({ month });
  const { data: cats, isLoading: catsLoading } = useCategories();
  const baseCurrency = useBaseCurrency();

  const catName = (id: number) =>
    cats?.find((c) => c.id === id)?.name ?? `#${id}`;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent transactions</CardTitle>
      </CardHeader>
      <CardContent>
        {txsLoading || catsLoading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-8" />)}
          </div>
        ) : (txs ?? []).length === 0 ? (
          <p className="text-sm text-muted-foreground italic">
            No transactions yet this month.
          </p>
        ) : (
          <ul className="divide-y">
            {(txs ?? []).slice(0, limit).map((t) => {
              const isForeign = t.currency !== baseCurrency;
              return (
                <li key={t.id} className="flex items-center justify-between py-2 text-sm">
                  <div>
                    <div className="font-medium">{t.description || catName(t.category_id)}</div>
                    <div className="text-xs text-muted-foreground">
                      {t.date} · {catName(t.category_id)}
                    </div>
                  </div>
                  <div className="text-right tabular-nums">
                    <div>{formatMoney(t.amount, t.currency)}</div>
                    {isForeign && (
                      <div className="text-xs text-muted-foreground">
                        {t.base_amount === null
                          ? "—"
                          : `≈ ${formatMoney(t.base_amount, baseCurrency)}`}
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
