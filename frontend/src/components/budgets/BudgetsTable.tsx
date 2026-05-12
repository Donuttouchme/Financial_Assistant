import { useState } from "react";
import { toast } from "sonner";
import { Check, X, AlertTriangle } from "lucide-react";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useCategories } from "@/hooks/queries/useCategories";
import { useBudgetsForMonth, useSetBudget } from "@/hooks/queries/useBudgets";
import { formatChf, parseChfInput } from "@/lib/currency";
import { cn } from "@/lib/utils";

interface Props { month: string }

function ProgressBar({ spent, limit }: { spent: number; limit: number }) {
  const pct = limit > 0 ? Math.min(100, (spent / limit) * 100) : 0;
  const over = spent > limit;
  return (
    <div className="w-full h-2 rounded bg-muted overflow-hidden">
      <div
        className={cn("h-full transition-all", over ? "bg-destructive" : "bg-primary")}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function BudgetsTable({ month }: Props) {
  const { data: cats, isLoading: catsLoading } = useCategories();
  const { data: budgets, isLoading: budgetsLoading } = useBudgetsForMonth(month);
  const setBudget = useSetBudget();

  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState("");

  if (catsLoading || budgetsLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
      </div>
    );
  }

  const expenseCats = (cats ?? []).filter((c) => c.kind === "expense");
  const budgetByCat = new Map(
    (budgets ?? []).map((b) => [b.category_id, b]),
  );

  if (expenseCats.length === 0) {
    return (
      <p className="text-sm text-muted-foreground italic py-8 text-center">
        No expense categories yet. Add some on the Categories page first.
      </p>
    );
  }

  function startEdit(categoryId: number, currentLimit: string) {
    setEditing(categoryId);
    setDraft(currentLimit);
  }

  function commitEdit(categoryId: number) {
    try {
      const cleaned = parseChfInput(draft);
      if (Number(cleaned) < 0) throw new Error("negative");
      setBudget.mutate(
        {
          categoryId,
          payload: { month, monthly_limit: cleaned },
        },
        { onSettled: () => setEditing(null) },
      );
    } catch {
      toast.error("Invalid amount");
      setEditing(null);
    }
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Category</TableHead>
          <TableHead>Limit</TableHead>
          <TableHead className="w-1/3">Progress</TableHead>
          <TableHead className="text-right">Spent</TableHead>
          <TableHead className="w-24" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {expenseCats.map((cat) => {
          const b = budgetByCat.get(cat.id);
          const limit = b ? Number(b.monthly_limit) : 0;
          const spent = b ? Number(b.spent) : 0;
          const over = b?.over_budget ?? false;
          const isEditing = editing === cat.id;

          return (
            <TableRow key={cat.id}>
              <TableCell>{cat.name}</TableCell>
              <TableCell>
                {isEditing ? (
                  <div className="flex items-center gap-1">
                    <Input
                      autoFocus
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      className="w-28 h-8"
                      placeholder="0.00"
                    />
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => commitEdit(cat.id)}
                      aria-label="Save"
                    >
                      <Check className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => setEditing(null)}
                      aria-label="Cancel"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ) : (
                  <span className="tabular-nums">
                    {b ? formatChf(b.monthly_limit) : "—"}
                  </span>
                )}
              </TableCell>
              <TableCell>
                <ProgressBar spent={spent} limit={limit} />
              </TableCell>
              <TableCell className="text-right tabular-nums">
                <span className={over ? "text-destructive font-medium" : ""}>
                  {b ? formatChf(b.spent) : "—"}
                </span>
                {over && (
                  <Badge variant="destructive" className="ml-2 gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    over
                  </Badge>
                )}
              </TableCell>
              <TableCell className="text-right">
                {!isEditing && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      startEdit(cat.id, b?.monthly_limit ?? "0")
                    }
                  >
                    {b ? "Edit" : "Set"}
                  </Button>
                )}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
