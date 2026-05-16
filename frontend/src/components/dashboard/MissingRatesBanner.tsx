import { AlertTriangle } from "lucide-react";
import { Link } from "react-router-dom";
import { useTransactions } from "@/hooks/queries/useTransactions";

interface Props { month: string }

export function MissingRatesBanner({ month }: Props) {
  const { data: txs } = useTransactions({ month });
  const missingCount = (txs ?? []).filter((t) => t.base_amount === null).length;
  if (missingCount === 0) return null;

  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm">
      <div className="flex items-center gap-2 text-amber-900 dark:text-amber-200">
        <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span>
          <strong>{missingCount}</strong>{" "}
          {missingCount === 1 ? "transaction is" : "transactions are"} excluded
          from totals — FX rate unavailable for {missingCount === 1 ? "its" : "their"} date.
        </span>
      </div>
      <Link
        to="/settings"
        className="text-amber-900 dark:text-amber-200 underline underline-offset-2 hover:no-underline whitespace-nowrap"
      >
        Refresh in Settings
      </Link>
    </div>
  );
}
