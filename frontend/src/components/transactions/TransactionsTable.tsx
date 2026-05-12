import { useState } from "react";
import { Pencil, Trash2, Repeat } from "lucide-react";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { TransactionFormDialog } from "@/components/transactions/TransactionFormDialog";
import {
  useTransactions, useDeleteTransaction,
} from "@/hooks/queries/useTransactions";
import { useCategories } from "@/hooks/queries/useCategories";
import { formatChf } from "@/lib/currency";
import type { Transaction } from "@/api/types";

interface Props {
  month: string;
  categoryId?: number;
}

export function TransactionsTable({ month, categoryId }: Props) {
  const { data: txs, isLoading } = useTransactions({
    month,
    category_id: categoryId,
  });
  const { data: cats } = useCategories();
  const del = useDeleteTransaction();

  const [editing, setEditing] = useState<Transaction | null>(null);
  const [confirm, setConfirm] = useState<Transaction | null>(null);

  const catName = (id: number) =>
    cats?.find((c) => c.id === id)?.name ?? `#${id}`;

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
      </div>
    );
  }

  if ((txs ?? []).length === 0) {
    return (
      <p className="text-sm text-muted-foreground italic py-8 text-center">
        No transactions for this month.
      </p>
    );
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-32">Date</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Description</TableHead>
            <TableHead className="text-right">Amount</TableHead>
            <TableHead className="w-24" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {txs!.map((t) => (
            <TableRow key={t.id}>
              <TableCell>{t.date}</TableCell>
              <TableCell>
                <span className="mr-2">{catName(t.category_id)}</span>
                {t.is_recurring && (
                  <Badge variant="outline" className="gap-1">
                    <Repeat className="h-3 w-3" /> recurring
                  </Badge>
                )}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {t.description || <span className="italic">—</span>}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {formatChf(t.amount)}
              </TableCell>
              <TableCell className="text-right">
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Edit ${t.description || t.id}`}
                  onClick={() => setEditing(t)}
                >
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Delete ${t.description || t.id}`}
                  onClick={() => setConfirm(t)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {editing && (
        <TransactionFormDialog
          mode="edit"
          open
          onOpenChange={(o) => !o && setEditing(null)}
          transaction={editing}
        />
      )}

      <AlertDialog
        open={confirm !== null}
        onOpenChange={(open) => !open && setConfirm(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete transaction?</AlertDialogTitle>
            <AlertDialogDescription>
              {confirm?.is_recurring
                ? "This is the recurring template. Deleting cancels future auto-generated entries; past entries stay."
                : "This cannot be undone."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (confirm) del.mutate(confirm.id);
                setConfirm(null);
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
