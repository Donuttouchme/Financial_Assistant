import { useEffect, useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { CurrencySelect } from "@/components/forms/CurrencySelect";
import {
  useRecurring, useUpdateRecurring, useDeleteRecurring,
} from "@/hooks/queries/useRecurring";
import { useCategories } from "@/hooks/queries/useCategories";
import { formatMoney, parseMoneyInput } from "@/lib/money";
import { isSupportedCurrency } from "@/lib/currencies";
import type { RecurringSchedule, RecurringUpdate } from "@/api/types";

const FREQUENCIES = ["monthly"] as const;

interface EditDialogProps {
  schedule: RecurringSchedule;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function EditScheduleDialog({ schedule, open, onOpenChange }: EditDialogProps) {
  const { data: categories } = useCategories();
  const update = useUpdateRecurring();

  // Form state. Amount is shown as a positive number (absolute value); we
  // re-apply the original sign on save so income/expense direction is preserved.
  const initialAmount = String(Math.abs(parseFloat(schedule.amount)).toFixed(2));
  const isNegative = parseFloat(schedule.amount) < 0;

  const [amount, setAmount] = useState(initialAmount);
  const [description, setDescription] = useState(schedule.description);
  const [categoryId, setCategoryId] = useState<number>(schedule.category_id);
  const [currency, setCurrency] = useState(schedule.currency);
  const [frequency, setFrequency] = useState(schedule.frequency);
  const [amountError, setAmountError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setAmount(String(Math.abs(parseFloat(schedule.amount)).toFixed(2)));
      setDescription(schedule.description);
      setCategoryId(schedule.category_id);
      setCurrency(schedule.currency);
      setFrequency(schedule.frequency);
      setAmountError(null);
    }
  }, [open, schedule]);

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();

    let cleanedAmount: string;
    try {
      cleanedAmount = parseMoneyInput(amount);
      if (Number(cleanedAmount) <= 0) throw new Error("must be positive");
    } catch {
      setAmountError("Must be a positive amount");
      return;
    }

    // Re-apply sign of the original amount.
    const signedAmount = isNegative
      ? "-" + cleanedAmount.replace(/^-/, "")
      : cleanedAmount;

    // Only send changed fields.
    const body: RecurringUpdate = {};
    if (signedAmount !== schedule.amount) body.amount = signedAmount;
    if (description !== schedule.description) body.description = description;
    if (categoryId !== schedule.category_id) body.category_id = categoryId;
    if (currency !== schedule.currency) body.currency = currency;
    if (frequency !== schedule.frequency) body.frequency = frequency;

    if (Object.keys(body).length === 0) {
      onOpenChange(false);
      return;
    }

    update.mutate(
      { id: schedule.id, body },
      { onSuccess: () => onOpenChange(false) },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <form onSubmit={onSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Edit recurring schedule</DialogTitle>
          </DialogHeader>

          <div className="space-y-2">
            <Label htmlFor="rec-amount">Amount</Label>
            <div className="flex gap-2">
              <Input
                id="rec-amount"
                value={amount}
                onChange={(e) => {
                  setAmount(e.target.value);
                  setAmountError(null);
                }}
                placeholder="0.00"
                className="flex-1"
                autoFocus
              />
              <div className="w-32">
                <CurrencySelect
                  id="rec-currency"
                  aria-label="Currency"
                  value={isSupportedCurrency(currency) ? currency : "CHF"}
                  onChange={setCurrency}
                />
              </div>
            </div>
            {amountError && (
              <p className="text-sm text-destructive">{amountError}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="rec-description">Description</Label>
            <Input
              id="rec-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="rec-category">Category</Label>
            <Select
              value={String(categoryId || "")}
              onValueChange={(v) => setCategoryId(Number(v))}
            >
              <SelectTrigger id="rec-category">
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
          </div>

          <div className="space-y-2">
            <Label htmlFor="rec-frequency">Frequency</Label>
            <Select value={frequency} onValueChange={setFrequency}>
              <SelectTrigger id="rec-frequency">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {FREQUENCIES.map((f) => (
                  <SelectItem key={f} value={f}>
                    {f}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={update.isPending}>
              {update.isPending ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function RecurringPage() {
  const { data: schedules, isLoading } = useRecurring();
  const { data: categories } = useCategories();
  const del = useDeleteRecurring();

  const [editing, setEditing] = useState<RecurringSchedule | null>(null);
  const [confirm, setConfirm] = useState<RecurringSchedule | null>(null);

  const catName = (id: number) =>
    categories?.find((c) => c.id === id)?.name ?? `#${id}`;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Recurring schedules</h2>

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
        </div>
      ) : (schedules ?? []).length === 0 ? (
        <p className="text-sm text-muted-foreground italic py-8 text-center">
          No recurring schedules yet. Create one by marking a transaction as recurring.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Description</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Currency</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Next occurrence</TableHead>
              <TableHead>Frequency</TableHead>
              <TableHead className="w-24" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {schedules!.map((s) => (
              <TableRow key={s.id}>
                <TableCell>
                  {s.description || <span className="italic">—</span>}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatMoney(s.amount, s.currency)}
                </TableCell>
                <TableCell>{s.currency}</TableCell>
                <TableCell>{catName(s.category_id)}</TableCell>
                <TableCell>{s.next_occurrence_date}</TableCell>
                <TableCell>{s.frequency}</TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Edit ${s.description || s.id}`}
                    onClick={() => setEditing(s)}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Delete ${s.description || s.id}`}
                    onClick={() => setConfirm(s)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {editing && (
        <EditScheduleDialog
          schedule={editing}
          open
          onOpenChange={(o) => !o && setEditing(null)}
        />
      )}

      <AlertDialog
        open={confirm !== null}
        onOpenChange={(open) => !open && setConfirm(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this recurring schedule?</AlertDialogTitle>
            <AlertDialogDescription>
              Past materialised transactions stay; future occurrences stop.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (confirm) del.mutate(confirm.id);
                setConfirm(null);
              }}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
