import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { CurrencySelect } from "@/components/forms/CurrencySelect";
import { useSettings, useUpdateBaseCurrency } from "@/hooks/queries/useSettings";

export function EmptyAppState() {
  const { data: settings } = useSettings();
  const update = useUpdateBaseCurrency();
  const [draft, setDraft] = useState<string>("CHF");

  useEffect(() => {
    if (settings?.base_currency) setDraft(settings.base_currency);
  }, [settings?.base_currency]);

  return (
    <Card>
      <CardContent className="py-12 flex flex-col items-center text-center gap-4">
        <h3 className="text-xl font-semibold">Welcome to Financial Assistant</h3>

        <div className="w-72 space-y-2 text-left">
          <Label htmlFor="welcome-currency">Default currency</Label>
          <div className="flex gap-2">
            <CurrencySelect id="welcome-currency" value={draft} onChange={setDraft} />
            <Button
              type="button"
              variant="secondary"
              disabled={draft === settings?.base_currency || update.isPending}
              onClick={() => update.mutate(draft)}
            >
              Save currency
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            You can change this anytime in Settings.
          </p>
        </div>

        <p className="text-muted-foreground max-w-md">
          Start by creating a few categories — income, expense, and savings buckets you
          want to track. Once you have at least one, you can add transactions and set budgets.
        </p>
        <Button asChild>
          <Link to="/categories">Create your first category</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
