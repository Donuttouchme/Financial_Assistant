import { useState } from "react";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useCategories, useDeleteCategory } from "@/hooks/queries/useCategories";
import type { Category } from "@/api/types";

export function CategoriesList() {
  const { data, isLoading } = useCategories();
  const del = useDeleteCategory();
  const [confirm, setConfirm] = useState<Category | null>(null);

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
      </div>
    );
  }

  const income = (data ?? []).filter((c) => c.kind === "income");
  const expense = (data ?? []).filter((c) => c.kind === "expense");
  const savings = (data ?? []).filter((c) => c.kind === "savings");

  function Section({ title, items }: { title: string; items: Category[] }) {
    return (
      <section>
        <h3 className="text-sm font-medium text-muted-foreground mb-2">
          {title}
        </h3>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground italic px-3">None yet.</p>
        ) : (
          <Card className="divide-y">
            {items.map((c) => (
              <div key={c.id} className="flex items-center justify-between px-3 py-2">
                <div className="flex items-center gap-2">
                  <span>{c.name}</span>
                  <Badge variant={
                    c.kind === "income" ? "default"
                    : c.kind === "savings" ? "outline"
                    : "secondary"
                  }>
                    {c.kind}
                  </Badge>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Delete ${c.name}`}
                  onClick={() => setConfirm(c)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </Card>
        )}
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <Section title="Income" items={income} />
      <Section title="Expense" items={expense} />
      <Section title="Savings" items={savings} />

      <AlertDialog
        open={confirm !== null}
        onOpenChange={(open) => !open && setConfirm(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete category?</AlertDialogTitle>
            <AlertDialogDescription>
              Deletes <b>{confirm?.name}</b>. Fails with a 409 error if any
              transaction still references it.
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
    </div>
  );
}
