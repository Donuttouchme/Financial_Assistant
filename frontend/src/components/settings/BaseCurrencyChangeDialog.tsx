import { useEffect, useState } from "react";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  usePreviewBaseCurrencyChange, useUpdateBaseCurrency,
} from "@/hooks/queries/useSettings";
import { formatMoney } from "@/lib/money";
import type { BaseCurrencyChangePreview } from "@/api/types";

interface Props {
  open: boolean;
  oldBase: string;
  newBase: string;
  onOpenChange: (open: boolean) => void;
}

export function BaseCurrencyChangeDialog({ open, oldBase, newBase, onOpenChange }: Props) {
  const preview = usePreviewBaseCurrencyChange();
  const commit = useUpdateBaseCurrency();
  const [data, setData] = useState<BaseCurrencyChangePreview | null>(null);

  useEffect(() => {
    if (open && newBase !== oldBase) {
      preview.mutate(newBase, { onSuccess: setData });
    } else if (!open) {
      setData(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, newBase, oldBase]);

  function confirm() {
    commit.mutate(newBase, { onSuccess: () => onOpenChange(false) });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Changing {oldBase} to {newBase}</DialogTitle>
        </DialogHeader>

        {preview.isPending || data === null ? (
          <Skeleton className="h-32 w-full" />
        ) : (
          <div className="space-y-4">
            {data.budgets.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-2">
                  Budgets ({data.budgets.length}) will be converted at today's rate
                </h4>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Category</TableHead>
                      <TableHead>Month</TableHead>
                      <TableHead className="text-right">Current</TableHead>
                      <TableHead className="text-right">After</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.budgets.map((b) => (
                      <TableRow key={`${b.category_id}-${b.month}`}>
                        <TableCell>{b.category_name}</TableCell>
                        <TableCell>{b.month}</TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatMoney(b.old_amount, oldBase)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatMoney(b.new_amount, newBase)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            {data.savings_goals.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-2">
                  Savings goals ({data.savings_goals.length})
                </h4>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Category</TableHead>
                      <TableHead className="text-right">Current</TableHead>
                      <TableHead className="text-right">After</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.savings_goals.map((g) => (
                      <TableRow key={g.category_id}>
                        <TableCell>{g.category_name}</TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatMoney(g.old_amount, oldBase)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatMoney(g.new_amount, newBase)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            {data.budgets.length === 0 && data.savings_goals.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No budgets or savings goals exist yet — the change is purely a default for
                new entries and the display unit on the dashboard.
              </p>
            )}

            <p className="text-xs text-muted-foreground">
              Existing transactions stay in their native currency. The dashboard will
              display all totals in {newBase} after the change.
            </p>
          </div>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button
            onClick={confirm}
            disabled={commit.isPending || data === null}
          >
            {commit.isPending ? "Converting…" : "Confirm"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
