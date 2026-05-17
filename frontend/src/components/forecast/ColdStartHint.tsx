import { Info } from "lucide-react";

interface Props {
  reason: "no-forecast" | "thin-data";
}

export function ColdStartHint({ reason }: Props) {
  const msg =
    reason === "no-forecast"
      ? "Forecast appears after about 30 days of activity."
      : "Forecast accuracy improves with more history (60+ days for full per-day projection).";
  return (
    <p className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
      <Info className="h-3.5 w-3.5" aria-hidden />
      <span>{msg}</span>
    </p>
  );
}
