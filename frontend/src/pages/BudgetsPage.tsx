import { BudgetsTable } from "@/components/budgets/BudgetsTable";
import { EmptyAppState } from "@/components/EmptyAppState";
import { useUrlMonth } from "@/hooks/useUrlMonth";
import { useCategories } from "@/hooks/queries/useCategories";
import { monthLabel } from "@/lib/date";

export default function BudgetsPage() {
  const { month } = useUrlMonth();
  const { data: cats, isLoading } = useCategories();

  if (!isLoading && (cats?.length ?? 0) === 0) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold">Budgets</h2>
        <EmptyAppState />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold">
          Budgets — {monthLabel(month)}
        </h2>
        <p className="text-sm text-muted-foreground">
          Limits set here apply from the current month forward. Past months keep their original values.
        </p>
      </div>
      <BudgetsTable month={month} />
    </div>
  );
}
