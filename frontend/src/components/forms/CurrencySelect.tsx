import { CURRENCY_SYMBOLS } from "@/lib/money";
import {
  CURRENCY_NAMES,
  MOST_USED,
  SUPPORTED_CURRENCIES,
  isSupportedCurrency,
} from "@/lib/currencies";

const OTHER_CURRENCIES = [...SUPPORTED_CURRENCIES]
  .filter((c) => !(MOST_USED as readonly string[]).includes(c))
  .sort((a, b) => a.localeCompare(b));

interface Props {
  value: string;
  onChange: (value: string) => void;
  id?: string;
  disabled?: boolean;
  className?: string;
  "aria-label"?: string;
}

function row(code: string): string {
  const symbol = CURRENCY_SYMBOLS[code] ?? code;
  const name = isSupportedCurrency(code) ? CURRENCY_NAMES[code] : code;
  return `${symbol}  ${code}  ${name}`;
}

export function CurrencySelect({ value, onChange, id, disabled, className, ...rest }: Props) {
  return (
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      aria-label={rest["aria-label"] ?? "Currency"}
      className={
        className ??
        "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
      }
    >
      <optgroup label="Most used">
        {MOST_USED.map((code) => (
          <option key={code} value={code}>
            {row(code)}
          </option>
        ))}
      </optgroup>
      <optgroup label="All currencies">
        {OTHER_CURRENCIES.map((code) => (
          <option key={code} value={code}>
            {row(code)}
          </option>
        ))}
      </optgroup>
    </select>
  );
}
