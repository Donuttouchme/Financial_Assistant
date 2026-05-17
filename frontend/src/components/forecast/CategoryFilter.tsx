import { useSearchParams } from "react-router-dom";

import type { Category } from "@/api/types";

interface Props {
  categories: Category[];
}

export function CategoryFilter({ categories }: Props) {
  const [search, setSearch] = useSearchParams();
  const current = search.get("category") ?? "all";

  return (
    <label className="inline-flex items-center gap-2 text-sm">
      <span className="text-muted-foreground">Category</span>
      <select
        aria-label="Category"
        className="h-8 rounded-md border bg-card px-2"
        value={current}
        onChange={(e) => {
          const next = new URLSearchParams(search);
          if (e.target.value === "all") next.delete("category");
          else next.set("category", e.target.value);
          setSearch(next, { replace: true });
        }}
      >
        <option value="all">All expense</option>
        {categories
          .filter((c) => c.kind === "expense")
          .map((c) => (
            <option key={c.id} value={String(c.id)}>{c.name}</option>
          ))}
      </select>
    </label>
  );
}
