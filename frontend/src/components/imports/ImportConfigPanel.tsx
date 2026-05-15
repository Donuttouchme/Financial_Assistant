import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CurrencySelect } from "@/components/forms/CurrencySelect";
import type { CsvImportConfig } from "@/api/types";

interface Props {
  config: CsvImportConfig;
  onChange: (next: CsvImportConfig) => void;
  defaultCurrency: string;
  onDefaultCurrencyChange: (v: string) => void;
}

export function ImportConfigPanel({
  config,
  onChange,
  defaultCurrency,
  onDefaultCurrencyChange,
}: Props) {
  function set<K extends keyof CsvImportConfig>(k: K, v: CsvImportConfig[K]) {
    onChange({ ...config, [k]: v });
  }
  function setCol<K extends keyof CsvImportConfig["cols"]>(
    k: K,
    v: number | null,
  ) {
    onChange({ ...config, cols: { ...config.cols, [k]: v } });
  }

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="cfg-default-currency">Default currency for this file</Label>
        <CurrencySelect
          id="cfg-default-currency"
          aria-label="Default currency"
          value={defaultCurrency}
          onChange={onDefaultCurrencyChange}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="cfg-delim">Delimiter</Label>
          <Select
            value={config.delimiter}
            onValueChange={(v) => set("delimiter", v)}
          >
            <SelectTrigger id="cfg-delim" aria-label="Delimiter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value=";">;</SelectItem>
              <SelectItem value=",">,</SelectItem>
              <SelectItem value="\t">tab</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="cfg-dec">Decimal separator</Label>
          <Select
            value={config.decimal_sep}
            onValueChange={(v) => set("decimal_sep", v)}
          >
            <SelectTrigger id="cfg-dec" aria-label="Decimal separator">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value=".">.</SelectItem>
              <SelectItem value=",">,</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="cfg-thou">Thousands separator</Label>
          <Select
            value={config.thousands_sep === "" ? "_none" : config.thousands_sep}
            onValueChange={(v) =>
              set("thousands_sep", v === "_none" ? "" : v)
            }
          >
            <SelectTrigger id="cfg-thou" aria-label="Thousands separator">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="_none">(none)</SelectItem>
              <SelectItem value="'">'</SelectItem>
              <SelectItem value=".">.</SelectItem>
              <SelectItem value=",">,</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="cfg-date">Date format (strftime)</Label>
          <Input
            id="cfg-date"
            value={config.date_format}
            onChange={(e) => set("date_format", e.target.value)}
            placeholder="%d.%m.%Y"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="cfg-skip">Skip header rows</Label>
          <Input
            id="cfg-skip"
            type="number"
            min={0}
            value={config.skip_header_rows}
            onChange={(e) =>
              set("skip_header_rows", Number(e.target.value))
            }
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="cfg-fmt">Amount format</Label>
          <Select
            value={config.amount_format}
            onValueChange={(v) =>
              set("amount_format", v as CsvImportConfig["amount_format"])
            }
          >
            <SelectTrigger id="cfg-fmt" aria-label="Amount format">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="signed">Single signed Amount</SelectItem>
              <SelectItem value="debit_credit">Separate Debit / Credit</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <div className="font-medium">Column mapping (0-based)</div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          <ColumnInput
            label="Date col"
            value={config.cols.date}
            onChange={(n) => setCol("date", n)}
          />
          <ColumnInput
            label="Description col"
            value={config.cols.description}
            onChange={(n) => setCol("description", n)}
          />
          {config.amount_format === "signed" ? (
            <ColumnInput
              label="Amount col"
              value={config.cols.amount ?? 0}
              onChange={(n) => setCol("amount", n)}
            />
          ) : (
            <>
              <ColumnInput
                label="Debit col"
                value={config.cols.debit ?? 0}
                onChange={(n) => setCol("debit", n)}
              />
              <ColumnInput
                label="Credit col"
                value={config.cols.credit ?? 0}
                onChange={(n) => setCol("credit", n)}
              />
            </>
          )}
          <ColumnInputOptional
            label="Currency col"
            value={config.cols.currency ?? null}
            onChange={(n) => setCol("currency", n)}
          />
        </div>
      </div>
    </div>
  );
}

function ColumnInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
}) {
  return (
    <div className="space-y-1">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Input
        type="number"
        min={0}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}

function ColumnInputOptional({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number | null;
  onChange: (n: number | null) => void;
}) {
  const id = `col-opt-${label.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <div className="space-y-1">
      <Label htmlFor={id} className="text-xs text-muted-foreground">{label}</Label>
      <Input
        id={id}
        type="number"
        min={0}
        value={value ?? ""}
        onChange={(e) =>
          onChange(e.target.value === "" ? null : Number(e.target.value))
        }
      />
    </div>
  );
}
