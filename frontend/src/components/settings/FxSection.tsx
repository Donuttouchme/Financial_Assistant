import { Button } from "@/components/ui/button";
import { useFxStatus, useRefreshFx } from "@/hooks/queries/useFx";
import { cn } from "@/lib/utils";

function ageColorClass(latest: string | null): string {
  // Gray reserved for the "never fetched" state. Once we have any rates,
  // freshness is green (today), blue (1-3 day window — normal on weekends
  // since ECB skips publishing), or amber (older than that).
  if (!latest) return "bg-gray-400";
  const today = new Date().toISOString().slice(0, 10);
  if (latest >= today) return "bg-emerald-500";
  const daysAgo = Math.floor(
    (Date.parse(today) - Date.parse(latest)) / (1000 * 60 * 60 * 24),
  );
  if (daysAgo <= 3) return "bg-sky-500";
  return "bg-amber-500";
}

function ageDescription(latest: string | null): string {
  if (!latest) return "Rates not yet fetched";
  const today = new Date().toISOString().slice(0, 10);
  if (latest >= today) return "Rates fresh (today)";
  const daysAgo = Math.floor(
    (Date.parse(today) - Date.parse(latest)) / (1000 * 60 * 60 * 24),
  );
  if (daysAgo <= 3) return `Rates ${daysAgo} day${daysAgo === 1 ? "" : "s"} old`;
  return `Rates ${daysAgo} days old — refresh recommended`;
}

export function FxSection() {
  const { data: status } = useFxStatus();
  const refresh = useRefreshFx();
  const latest = status?.latest_date ?? null;
  const colorClass = ageColorClass(latest);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm">
        <span
          className={cn("h-2 w-2 rounded-full", colorClass)}
          aria-label={ageDescription(latest)}
          role="img"
        />
        <span>
          {latest === null
            ? "Rates not yet fetched"
            : <>Rates as of <span className="font-mono">{latest}</span></>}
        </span>
      </div>
      <Button
        type="button"
        variant="secondary"
        disabled={refresh.isPending}
        onClick={() => refresh.mutate()}
      >
        {refresh.isPending ? "Refreshing…" : "Refresh rates now"}
      </Button>
      <p className="text-xs text-muted-foreground">
        Source: frankfurter.dev (European Central Bank reference rates).
        ECB publishes rates once per business day around 16:00 CET.
      </p>
    </div>
  );
}
