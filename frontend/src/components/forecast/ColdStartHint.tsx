import { Sparkles } from "lucide-react";

/**
 * Empty-state placeholder rendered inside the forecast chart card when the
 * user has no expense history at all. Keeps the widget visible (same chrome,
 * same height as the chart) so adding the first transaction reveals data in
 * place rather than swapping cards.
 */
export function ForecastEmptyState() {
  return (
    <div className="h-72 w-full flex flex-col items-center justify-center text-center gap-2 text-muted-foreground">
      <Sparkles className="h-6 w-6 opacity-60" aria-hidden />
      <p className="text-sm">
        Your forecast will appear here as you add transactions.
      </p>
      <p className="text-xs opacity-80">
        The graph sharpens automatically once a few weeks of activity are on file.
      </p>
    </div>
  );
}
