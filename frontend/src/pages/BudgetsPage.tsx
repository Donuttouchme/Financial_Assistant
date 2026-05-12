import { BudgetsTable } from "@/components/budgets/BudgetsTable";
import { useUrlMonth } from "@/hooks/useUrlMonth";
import { monthLabel } from "@/lib/date";

export default function BudgetsPage() {
  const { month } = useUrlMonth();
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">
        Budgets — {monthLabel(month)}
      </h2>
      <BudgetsTable month={month} />
    </div>
  );
}
