import { useSearchParams } from "react-router-dom";

import { cn } from "@/lib/utils";
import type { ForecastMode } from "@/api/types";

const OPTIONS: { value: ForecastMode; label: string }[] = [
  { value: "centered", label: "Centered on today" },
  { value: "forward", label: "Forecast only" },
];

export function ForecastModeToggle() {
  const [search, setSearch] = useSearchParams();
  const current = (search.get("mode") as ForecastMode) || "centered";

  return (
    <div
      role="radiogroup"
      aria-label="Forecast mode"
      className="inline-flex rounded-md border bg-card p-0.5"
    >
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          role="radio"
          aria-checked={current === opt.value}
          onClick={() => {
            const next = new URLSearchParams(search);
            if (opt.value === "centered") next.delete("mode");
            else next.set("mode", opt.value);
            setSearch(next, { replace: true });
          }}
          className={cn(
            "px-3 h-7 text-xs rounded",
            current === opt.value
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-foreground",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
