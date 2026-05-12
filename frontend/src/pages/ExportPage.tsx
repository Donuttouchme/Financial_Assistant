import { useState } from "react";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { downloadTransactionsCsv } from "@/api/export";
import { HttpError } from "@/api/client";
import { useUrlMonth } from "@/hooks/useUrlMonth";
import { monthOptions } from "@/lib/date";

function triggerBrowserDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function ExportPage() {
  const { month: globalMonth } = useUrlMonth();
  const [scope, setScope] = useState<string>(globalMonth);
  const [isPending, setPending] = useState(false);

  async function onDownload() {
    setPending(true);
    try {
      const target = scope === "all" ? undefined : scope;
      const blob = await downloadTransactionsCsv(target);
      const filename = `transactions-${target ?? "all"}.csv`;
      triggerBrowserDownload(blob, filename);
      toast.success(`Downloaded ${filename}`);
    } catch (err) {
      toast.error(
        err instanceof HttpError ? err.detail : "Download failed",
      );
    } finally {
      setPending(false);
    }
  }

  const opts = monthOptions();

  return (
    <div className="max-w-xl space-y-6">
      <h2 className="text-2xl font-semibold">Export</h2>
      <Card>
        <CardHeader>
          <CardTitle>Download transactions as CSV</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="export-scope">Scope</Label>
            <Select value={scope} onValueChange={setScope}>
              <SelectTrigger id="export-scope">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All transactions</SelectItem>
                {opts.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={onDownload} disabled={isPending}>
            <Download className="h-4 w-4 mr-2" />
            {isPending ? "Preparing…" : "Download CSV"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
