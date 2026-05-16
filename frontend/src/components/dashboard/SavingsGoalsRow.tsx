import { useMemo } from "react";
import { useCategories } from "@/hooks/queries/useCategories";
import { useTransactions } from "@/hooks/queries/useTransactions";
import { useBaseCurrency } from "@/hooks/queries/useSettings";
import { SavingsGoalCard } from "./SavingsGoalCard";
import { Skeleton } from "@/components/ui/skeleton";

interface Props {
  month: string;  // currently unused except as a key for layout consistency
}

export function SavingsGoalsRow({ month: _month }: Props) {
  const { data: cats, isLoading: catsLoading } = useCategories();
  // Cumulative goal progress — fetch ALL savings transactions, not just current month.
  const { data: allTxs, isLoading: txsLoading } = useTransactions({});
  const baseCurrency = useBaseCurrency();

  const cards = useMemo(() => {
    if (!cats || !allTxs) return [];
    const savings = cats.filter((c) => c.kind === "savings");
    const sumsByCat = new Map<number, number>();
    for (const t of allTxs) {
      if (t.base_amount === null) continue;
      sumsByCat.set(t.category_id, (sumsByCat.get(t.category_id) ?? 0) + Number(t.base_amount));
    }
    return savings.map((c) => ({
      id: c.id,
      name: c.name,
      saved: sumsByCat.get(c.id) ?? 0,
      target: c.target_amount === null ? null : Number(c.target_amount),
      targetDate: c.target_date,
    }));
  }, [cats, allTxs]);

  if (catsLoading || txsLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
      </div>
    );
  }

  if (cards.length === 0) return null;

  return (
    <section>
      <h3 className="text-lg font-medium mb-3">Savings goals</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cards.map((c) => (
          <SavingsGoalCard
            key={c.id}
            name={c.name}
            saved={c.saved}
            target={c.target}
            targetDate={c.targetDate}
            currency={baseCurrency}
          />
        ))}
      </div>
    </section>
  );
}
