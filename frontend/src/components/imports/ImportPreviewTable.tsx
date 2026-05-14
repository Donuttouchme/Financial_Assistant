import { useEffect, useMemo, useState } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  Category,
  ImportCommitRowSelection,
  ParsedRow,
} from "@/api/types";
import { cn } from "@/lib/utils";

interface Props {
  rows: ParsedRow[];
  categories: Category[];
  defaultCategoryId: number;
  onSelectionsChange: (sel: ImportCommitRowSelection[]) => void;
}

export function ImportPreviewTable({
  rows,
  categories,
  defaultCategoryId,
  onSelectionsChange,
}: Props) {
  const eligibleIndexes = useMemo(
    () =>
      new Set(
        rows
          .filter(
            (r) =>
              r.errors.length === 0 && r.amount !== null && r.date !== null,
          )
          .map((r) => r.row_index),
      ),
    [rows],
  );

  const initialTicked = useMemo(
    () =>
      new Set(
        rows
          .filter(
            (r) =>
              !r.is_duplicate &&
              r.errors.length === 0 &&
              r.amount !== null &&
              r.date !== null,
          )
          .map((r) => r.row_index),
      ),
    [rows],
  );

  const initialCatId = useMemo(() => {
    const m = new Map<number, number>();
    for (const r of rows) m.set(r.row_index, defaultCategoryId);
    return m;
  }, [rows, defaultCategoryId]);

  const [ticked, setTicked] = useState<Set<number>>(initialTicked);
  const [catByRow, setCatByRow] = useState<Map<number, number>>(initialCatId);

  // Reset state when rows change (e.g., user re-previews with a different config).
  useEffect(() => {
    setTicked(initialTicked);
    setCatByRow(initialCatId);
  }, [initialTicked, initialCatId]);

  useEffect(() => {
    const sel: ImportCommitRowSelection[] = [];
    for (const r of rows) {
      if (!ticked.has(r.row_index)) continue;
      sel.push({
        row_index: r.row_index,
        category_id: catByRow.get(r.row_index) ?? defaultCategoryId,
        is_recurring: false,
      });
    }
    onSelectionsChange(sel);
  }, [ticked, catByRow, rows, defaultCategoryId, onSelectionsChange]);

  function toggleRow(idx: number) {
    setTicked((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }

  function setRowCat(idx: number, catId: number) {
    setCatByRow((prev) => new Map(prev).set(idx, catId));
  }

  function bulkSetCat(catId: number) {
    setCatByRow((prev) => {
      const next = new Map(prev);
      for (const idx of ticked) next.set(idx, catId);
      return next;
    });
  }

  const allEligibleTicked =
    eligibleIndexes.size > 0 && ticked.size === eligibleIndexes.size;

  return (
    <div className="space-y-2">
      <BulkBar
        categories={categories}
        tickedCount={ticked.size}
        onBulkCategory={bulkSetCat}
      />
      <div className="border rounded-md overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted">
            <tr>
              <th className="p-2 text-left w-8">
                <Checkbox
                  aria-label="Select all eligible rows"
                  checked={allEligibleTicked}
                  onCheckedChange={(c) => {
                    if (c) setTicked(new Set(eligibleIndexes));
                    else setTicked(new Set());
                  }}
                />
              </th>
              <th className="p-2 text-left">Date</th>
              <th className="p-2 text-left">Description</th>
              <th className="p-2 text-right">Amount</th>
              <th className="p-2 text-left">Category</th>
              <th className="p-2 text-left">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const isTicked = ticked.has(r.row_index);
              const ineligible =
                r.errors.length > 0 ||
                r.amount === null ||
                r.date === null;
              return (
                <tr
                  key={r.row_index}
                  className={cn(
                    "border-t",
                    r.is_duplicate && "opacity-60",
                    r.errors.length > 0 && "bg-destructive/10",
                  )}
                >
                  <td className="p-2">
                    <Checkbox
                      aria-label={`Select row ${r.row_index + 1}`}
                      checked={isTicked}
                      onCheckedChange={() => toggleRow(r.row_index)}
                      disabled={ineligible}
                    />
                  </td>
                  <td className="p-2">{r.date ?? "—"}</td>
                  <td className="p-2">{r.description}</td>
                  <td className="p-2 text-right tabular-nums">
                    {r.amount ?? "—"}
                  </td>
                  <td className="p-2">
                    <Select
                      value={String(
                        catByRow.get(r.row_index) ?? defaultCategoryId,
                      )}
                      onValueChange={(v) => setRowCat(r.row_index, Number(v))}
                    >
                      <SelectTrigger className="h-8 w-40">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {categories.map((c) => (
                          <SelectItem key={c.id} value={String(c.id)}>
                            {c.name} ({c.kind})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </td>
                  <td className="p-2 text-xs">
                    {r.errors.length > 0 ? (
                      <span className="text-destructive">{r.errors[0]}</span>
                    ) : r.is_duplicate ? (
                      <span className="text-muted-foreground">Duplicate</span>
                    ) : (
                      <span className="text-emerald-600 dark:text-emerald-500">
                        New
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function BulkBar({
  categories,
  tickedCount,
  onBulkCategory,
}: {
  categories: Category[];
  tickedCount: number;
  onBulkCategory: (catId: number) => void;
}) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-muted-foreground">{tickedCount} ticked</span>
      <span className="text-muted-foreground">·</span>
      <span>Set category for all ticked:</span>
      <Select onValueChange={(v) => onBulkCategory(Number(v))}>
        <SelectTrigger className="h-8 w-44">
          <SelectValue placeholder="— pick —" />
        </SelectTrigger>
        <SelectContent>
          {categories.map((c) => (
            <SelectItem key={c.id} value={String(c.id)}>
              {c.name} ({c.kind})
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
