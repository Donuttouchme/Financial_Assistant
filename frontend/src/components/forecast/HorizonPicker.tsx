import { useSearchParams } from "react-router-dom";

import { cn } from "@/lib/utils";
import type { ForecastHorizon } from "@/api/types";

const OPTIONS: ForecastHorizon[] = ["1m", "3m", "6m", "1y", "2y"];
const LABEL: Record<ForecastHorizon, string> = {
  "1m": "1 month", "3m": "3 months", "6m": "6 months",
  "1y": "1 year", "2y": "2 years",
};

export function HorizonPicker() {
  const [search, setSearch] = useSearchParams();
  const current = (search.get("horizon") as ForecastHorizon) || "6m";

  return (
    <div
      role="radiogroup"
      aria-label="Horizon"
      className="inline-flex rounded-md border bg-card p-0.5"
    >
      {OPTIONS.map((h) => (
        <button
          key={h}
          type="button"
          role="radio"
          aria-checked={current === h}
          onClick={() => {
            const next = new URLSearchParams(search);
            next.set("horizon", h);
            setSearch(next, { replace: true });
          }}
          className={cn(
            "px-3 h-7 text-xs rounded",
            current === h
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-foreground",
          )}
        >
          {LABEL[h]}
        </button>
      ))}
    </div>
  );
}
