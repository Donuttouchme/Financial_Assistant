import { KpiRow } from "@/components/dashboard/KpiRow";
import { BudgetWidget } from "@/components/dashboard/BudgetWidget";
import { RecentTransactions } from "@/components/dashboard/RecentTransactions";
import { CategoryDonut } from "@/components/dashboard/CategoryDonut";
import { MonthlyTrendBar } from "@/components/dashboard/MonthlyTrendBar";
import { SavingsGoalsRow } from "@/components/dashboard/SavingsGoalsRow";
import { MissingRatesBanner } from "@/components/dashboard/MissingRatesBanner";
import { EmptyAppState } from "@/components/EmptyAppState";
import { useUrlMonth } from "@/hooks/useUrlMonth";
import { useCategories } from "@/hooks/queries/useCategories";
import { monthLabel } from "@/lib/date";

export default function DashboardPage() {
  const { month } = useUrlMonth();
  const { data: cats, isLoading } = useCategories();

  if (!isLoading && (cats?.length ?? 0) === 0) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold">Dashboard</h2>
        <EmptyAppState />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Dashboard — {monthLabel(month)}</h2>
      <MissingRatesBanner month={month} />
      <KpiRow month={month} />
      <SavingsGoalsRow month={month} />
      <BudgetWidget month={month} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <CategoryDonut month={month} />
        <MonthlyTrendBar month={month} />
      </div>
      <RecentTransactions month={month} />
    </div>
  );
}
