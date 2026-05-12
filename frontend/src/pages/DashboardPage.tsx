import { KpiRow } from "@/components/dashboard/KpiRow";
import { OverBudgetAlerts } from "@/components/dashboard/OverBudgetAlerts";
import { RecentTransactions } from "@/components/dashboard/RecentTransactions";
import { CategoryDonut } from "@/components/dashboard/CategoryDonut";
import { MonthlyTrendBar } from "@/components/dashboard/MonthlyTrendBar";
import { useUrlMonth } from "@/hooks/useUrlMonth";
import { monthLabel } from "@/lib/date";

export default function DashboardPage() {
  const { month } = useUrlMonth();
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">
        Dashboard — {monthLabel(month)}
      </h2>
      <KpiRow month={month} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <CategoryDonut month={month} />
        <MonthlyTrendBar month={month} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <OverBudgetAlerts month={month} />
        <RecentTransactions month={month} />
      </div>
    </div>
  );
}
