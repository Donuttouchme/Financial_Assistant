import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { CurrencySelect } from "@/components/forms/CurrencySelect";
import { useBaseCurrency } from "@/hooks/queries/useSettings";
import { BaseCurrencyChangeDialog } from "./BaseCurrencyChangeDialog";

export function CurrencySection() {
  const current = useBaseCurrency();
  const [draft, setDraft] = useState<string>(current);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    setDraft(current);
  }, [current]);

  return (
    <div className="space-y-3">
      <Label htmlFor="base-currency">Base currency</Label>
      <div className="flex gap-2">
        <CurrencySelect id="base-currency" value={draft} onChange={setDraft} />
        <Button
          type="button"
          variant="secondary"
          disabled={draft === current}
          onClick={() => setDialogOpen(true)}
        >
          Change base currency
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">
        All dashboard totals are shown in this currency. Existing budgets and savings
        goals will be converted at today's rate when you change it.
      </p>

      <BaseCurrencyChangeDialog
        open={dialogOpen}
        oldBase={current}
        newBase={draft}
        onOpenChange={(o) => {
          setDialogOpen(o);
          if (!o) setDraft(current);
        }}
      />
    </div>
  );
}
