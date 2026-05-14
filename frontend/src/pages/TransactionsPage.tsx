import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { TransactionsTable } from "@/components/transactions/TransactionsTable";
import { EmptyAppState } from "@/components/EmptyAppState";
import { useUrlMonth } from "@/hooks/useUrlMonth";
import { useCategories } from "@/hooks/queries/useCategories";
import { useSearchParams } from "react-router-dom";
import { monthLabel } from "@/lib/date";

export default function TransactionsPage() {
  const { month } = useUrlMonth();
  const { data: cats, isLoading } = useCategories();
  const [params, setParams] = useSearchParams();
  const catParam = params.get("category_id");
  const categoryId = catParam ? Number(catParam) : undefined;

  function onCategoryChange(next: string) {
    const np = new URLSearchParams(params);
    if (next === "all") np.delete("category_id");
    else np.set("category_id", next);
    setParams(np);
  }

  if (!isLoading && (cats?.length ?? 0) === 0) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold">Transactions</h2>
        <EmptyAppState />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">
          Transactions — {monthLabel(month)}
        </h2>
        <div className="flex items-end gap-2">
          <div>
            <Label htmlFor="tx-cat-filter" className="text-xs text-muted-foreground">
              Category
            </Label>
            <Select
              value={categoryId ? String(categoryId) : "all"}
              onValueChange={onCategoryChange}
            >
              <SelectTrigger id="tx-cat-filter" className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {(cats ?? []).map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
      <TransactionsTable month={month} categoryId={categoryId} />
    </div>
  );
}
