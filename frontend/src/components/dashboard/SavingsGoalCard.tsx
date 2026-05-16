import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { formatMoney } from "@/lib/money";

interface Props {
  name: string;
  saved: number;
  target: number | null;
  targetDate: string | null;  // ISO YYYY-MM-DD
  today?: Date;
  currency?: string;
}

function daysBetween(from: Date, toIso: string): number {
  const to = new Date(toIso + "T00:00:00");
  return Math.max(0, Math.round((to.getTime() - from.getTime()) / 86_400_000));
}

export function SavingsGoalCard({ name, saved, target, targetDate, today, currency = "CHF" }: Props) {
  const now = today ?? new Date();
  const pct =
    target && target > 0 ? Math.min(100, Math.max(0, (saved / target) * 100)) : null;
  const days = targetDate ? daysBetween(now, targetDate) : null;
  const tone =
    pct === null
      ? "text-muted-foreground"
      : pct >= 100
      ? "text-emerald-600 dark:text-emerald-500"
      : pct >= 80
      ? "text-amber-600 dark:text-amber-400"
      : "";

  return (
    <Card>
      <CardContent className="py-4 space-y-2">
        <div className="font-medium">{name}</div>
        {target !== null ? (
          <>
            <div className="flex items-baseline gap-2">
              <span className="text-lg font-semibold tabular-nums">
                {formatMoney(saved, currency)}
              </span>
              <span className="text-muted-foreground text-sm">
                / {formatMoney(target, currency)}
              </span>
              <span className={`ml-auto text-sm font-medium ${tone}`}>
                {pct?.toFixed(0)}%
              </span>
            </div>
            <Progress value={pct ?? 0} />
            <div className="text-xs text-muted-foreground">
              {targetDate ? `${days} days left` : "no deadline"}
            </div>
          </>
        ) : (
          <div className="text-sm">
            <span className="tabular-nums">{formatMoney(saved, currency)}</span>{" "}
            <span className="text-muted-foreground">saved</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
