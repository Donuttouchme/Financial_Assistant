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
import { useCreateCategory } from "@/hooks/queries/useCategories";
import { parseMoneyInput } from "@/lib/money";
import { useSettings } from "@/hooks/queries/useSettings";

const schema = z
  .object({
    name: z.string().min(1, "Required").max(80),
    kind: z.enum(["income", "expense", "savings"]),
    target_amount: z.string().optional().default(""),
    target_date: z.string().optional().default(""),
  })
  .superRefine((v, ctx) => {
    if (v.kind !== "savings") {
      if (v.target_amount || v.target_date) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["target_amount"],
          message: "Targets only allowed on savings categories",
        });
      }
      return;
    }
    if (v.target_amount) {
      try {
        const n = Number(parseMoneyInput(v.target_amount));
        if (!(n > 0)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ["target_amount"],
            message: "Must be a positive amount",
          });
        }
      } catch {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["target_amount"],
          message: "Invalid amount",
        });
      }
    }
    if (v.target_date && !/^\d{4}-\d{2}-\d{2}$/.test(v.target_date)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["target_date"],
        message: "YYYY-MM-DD",
      });
    }
  });
type FormValues = z.infer<typeof schema>;

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CategoryFormDialog({ open, onOpenChange }: Props) {
  const create = useCreateCategory();
  const { data: settings } = useSettings();
  const baseCurrency = settings?.base_currency ?? "CHF";
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", kind: "expense", target_amount: "", target_date: "" },
  });

  const kind = form.watch("kind");

  function onSubmit(values: FormValues) {
    create.mutate(
      {
        name: values.name,
        kind: values.kind,
        target_amount:
          values.kind === "savings" && values.target_amount
            ? parseMoneyInput(values.target_amount)
            : null,
        target_date:
          values.kind === "savings" && values.target_date
            ? values.target_date
            : null,
      },
      {
        onSuccess: () => {
          form.reset();
          onOpenChange(false);
        },
      },
    );
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) form.reset();
        onOpenChange(o);
      }}
    >
      <DialogContent>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <DialogHeader>
            <DialogTitle>New category</DialogTitle>
          </DialogHeader>

          <div className="space-y-2">
            <Label htmlFor="cat-name">Name</Label>
            <Input id="cat-name" {...form.register("name")} autoFocus />
            {form.formState.errors.name && (
              <p className="text-sm text-destructive">
                {form.formState.errors.name.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="cat-kind">Kind</Label>
            <Select
              value={form.watch("kind")}
              onValueChange={(v) => {
                const next = v as FormValues["kind"];
                form.setValue("kind", next, { shouldValidate: true });
                if (next !== "savings") {
                  form.setValue("target_amount", "");
                  form.setValue("target_date", "");
                }
              }}
            >
              <SelectTrigger id="cat-kind" aria-label="Kind">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="expense">Expense</SelectItem>
                <SelectItem value="income">Income</SelectItem>
                <SelectItem value="savings">Savings</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {kind === "savings" && (
            <>
              <div className="space-y-2">
                <Label htmlFor="cat-target-amount">Target amount ({baseCurrency}, optional)</Label>
                <Input
                  id="cat-target-amount"
                  placeholder="0.00"
                  {...form.register("target_amount")}
                />
                {form.formState.errors.target_amount && (
                  <p className="text-sm text-destructive">
                    {form.formState.errors.target_amount.message}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="cat-target-date">Target date (optional)</Label>
                <Input
                  id="cat-target-date"
                  type="date"
                  {...form.register("target_date")}
                />
                {form.formState.errors.target_date && (
                  <p className="text-sm text-destructive">
                    {form.formState.errors.target_date.message}
                  </p>
                )}
              </div>
            </>
          )}

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
