import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useCategories } from "@/hooks/queries/useCategories";
import {
  useCreateTransaction, useUpdateTransaction,
} from "@/hooks/queries/useTransactions";
import type { Transaction } from "@/api/types";
import { parseChfInput } from "@/lib/currency";

const schema = z.object({
  amount: z
    .string()
    .min(1, "Required")
    .refine((s) => {
      try {
        const n = Number(parseChfInput(s));
        return n > 0;
      } catch {
        return false;
      }
    }, "Must be a positive amount"),
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "YYYY-MM-DD"),
  category_id: z.coerce.number().int().positive("Pick a category"),
  description: z.string().max(255).default(""),
  is_recurring: z.boolean().default(false),
  direction: z.enum(["deposit", "withdraw"]).default("deposit"),
});
type FormValues = z.infer<typeof schema>;

interface CreateProps {
  mode: "create";
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialDate?: string;
}
interface EditProps {
  mode: "edit";
  open: boolean;
  onOpenChange: (open: boolean) => void;
  transaction: Transaction;
}
type Props = CreateProps | EditProps;

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function TransactionFormDialog(props: Props) {
  const { open, onOpenChange } = props;
  const isEdit = props.mode === "edit";

  const { data: categories } = useCategories();
  const create = useCreateTransaction();
  const update = useUpdateTransaction();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: isEdit
      ? {
          amount: String(Math.abs(parseFloat(props.transaction.amount))),
          date: props.transaction.date,
          category_id: props.transaction.category_id,
          description: props.transaction.description,
          is_recurring: props.transaction.is_recurring,
          direction: parseFloat(props.transaction.amount) < 0 ? "withdraw" : "deposit",
        }
      : {
          amount: "",
          date: props.initialDate ?? todayIso(),
          category_id: 0,
          description: "",
          is_recurring: false,
          direction: "deposit",
        },
  });

  // When the dialog reopens (mostly in edit mode with a different transaction),
  // re-seed the form with the current props.
  useEffect(() => {
    if (open) {
      if (isEdit) {
        const amt = parseFloat(props.transaction.amount);
        const dir = amt < 0 ? "withdraw" : "deposit";
        form.reset({
          amount: String(Math.abs(amt)),
          date: props.transaction.date,
          category_id: props.transaction.category_id,
          description: props.transaction.description,
          is_recurring: props.transaction.is_recurring,
          direction: dir,
        });
      } else {
        form.reset({
          amount: "",
          date: props.initialDate ?? todayIso(),
          category_id: 0,
          description: "",
          is_recurring: false,
          direction: "deposit",
        });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, isEdit, isEdit ? props.transaction.id : null]);

  const selectedCategoryId = form.watch("category_id");
  const selectedCategory = (categories ?? []).find((c) => c.id === selectedCategoryId);
  const isSavings = selectedCategory?.kind === "savings";
  const direction = form.watch("direction") ?? "deposit";

  function onSubmit(values: FormValues) {
    let amount = parseChfInput(values.amount);
    if (selectedCategory?.kind === "savings" && values.direction === "withdraw") {
      // Always produce a single leading minus, regardless of existing prefix.
      amount = "-" + amount.replace(/^-/, "");
    }
    if (isEdit) {
      update.mutate(
        {
          id: props.transaction.id,
          payload: {
            amount,
            date: values.date,
            category_id: values.category_id,
            description: values.description,
          },
        },
        { onSuccess: () => onOpenChange(false) },
      );
    } else {
      create.mutate(
        {
          amount,
          date: values.date,
          category_id: values.category_id,
          description: values.description,
          is_recurring: values.is_recurring,
        },
        { onSuccess: () => onOpenChange(false) },
      );
    }
  }

  const submitting = create.isPending || update.isPending;

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) form.reset();
        onOpenChange(o);
      }}
    >
      <DialogContent className="max-w-md">
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <DialogHeader>
            <DialogTitle>{isEdit ? "Edit transaction" : "Add transaction"}</DialogTitle>
          </DialogHeader>

          <div className="space-y-2">
            <Label htmlFor="tx-amount">Amount (CHF)</Label>
            <Input id="tx-amount" placeholder="0.00" {...form.register("amount")} autoFocus />
            {form.formState.errors.amount && (
              <p className="text-sm text-destructive">
                {form.formState.errors.amount.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="tx-date">Date</Label>
            <Input id="tx-date" type="date" {...form.register("date")} />
            {form.formState.errors.date && (
              <p className="text-sm text-destructive">
                {form.formState.errors.date.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="tx-category">Category</Label>
            <Select
              value={String(form.watch("category_id") || "")}
              onValueChange={(v) =>
                form.setValue("category_id", Number(v), { shouldValidate: true })
              }
            >
              <SelectTrigger id="tx-category">
                <SelectValue placeholder="Pick a category" />
              </SelectTrigger>
              <SelectContent>
                {(categories ?? []).map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>
                    {c.name} ({c.kind})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {form.formState.errors.category_id && (
              <p className="text-sm text-destructive">
                {form.formState.errors.category_id.message}
              </p>
            )}
          </div>

          {isSavings && (
            <div role="group" aria-label="Direction" className="space-y-2">
              <Label>Direction</Label>
              <ToggleGroup
                type="single"
                value={direction}
                onValueChange={(v) => {
                  if (v) form.setValue("direction", v as "deposit" | "withdraw");
                }}
              >
                <ToggleGroupItem value="deposit" aria-label="Deposit">
                  ↑ Deposit
                </ToggleGroupItem>
                <ToggleGroupItem value="withdraw" aria-label="Withdraw">
                  ↓ Withdraw
                </ToggleGroupItem>
              </ToggleGroup>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="tx-description">Description</Label>
            <Input id="tx-description" {...form.register("description")} />
          </div>

          {!isEdit && (
            <div className="flex items-center gap-2">
              <Switch
                id="tx-recurring"
                checked={form.watch("is_recurring")}
                onCheckedChange={(v) => form.setValue("is_recurring", v)}
              />
              <Label htmlFor="tx-recurring" className="cursor-pointer">
                Monthly recurring
              </Label>
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Saving…" : isEdit ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
