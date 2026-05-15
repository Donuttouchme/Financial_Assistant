import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { CurrencySection } from "@/components/settings/CurrencySection";

export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-2xl font-semibold">Settings</h2>

      <Card>
        <CardHeader>
          <h3 className="text-2xl font-semibold leading-none tracking-tight">Currency</h3>
        </CardHeader>
        <CardContent>
          <CurrencySection />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h3 className="text-2xl font-semibold leading-none tracking-tight">Exchange rates</h3>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">FX section.</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h3 className="text-2xl font-semibold leading-none tracking-tight">Appearance</h3>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Appearance section.</div>
        </CardContent>
      </Card>
    </div>
  );
}
