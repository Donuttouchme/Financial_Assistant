import { useMemo } from "react";
import { CURRENCY_SYMBOLS } from "@/lib/money";
import { MOST_USED, SUPPORTED_CURRENCIES } from "@/lib/currencies";

const CURRENCY_NAMES: Record<string, string> = {
  AUD: "Australian Dollar", BGN: "Bulgarian Lev", BRL: "Brazilian Real",
  CAD: "Canadian Dollar", CHF: "Swiss Franc", CNY: "Chinese Yuan",
  CZK: "Czech Koruna", DKK: "Danish Krone", EUR: "Euro",
  GBP: "Pound Sterling", HKD: "Hong Kong Dollar", HUF: "Hungarian Forint",
  IDR: "Indonesian Rupiah", ILS: "Israeli Shekel", INR: "Indian Rupee",
  ISK: "Icelandic Króna", JPY: "Japanese Yen", KRW: "South Korean Won",
  MXN: "Mexican Peso", MYR: "Malaysian Ringgit", NOK: "Norwegian Krone",
  NZD: "New Zealand Dollar", PHP: "Philippine Peso", PLN: "Polish Zloty",
  RON: "Romanian Leu", SEK: "Swedish Krona", SGD: "Singapore Dollar",
  THB: "Thai Baht", TRY: "Turkish Lira", USD: "US Dollar",
  ZAR: "South African Rand",
};

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
  const name = CURRENCY_NAMES[code] ?? code;
  return `${symbol}  ${code}  ${name}`;
}

export function CurrencySelect({ value, onChange, id, disabled, className, ...rest }: Props) {
  const others = useMemo(
    () =>
      [...SUPPORTED_CURRENCIES]
        .filter((c) => !(MOST_USED as readonly string[]).includes(c))
        .sort((a, b) => a.localeCompare(b)),
    [],
  );

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
        {others.map((code) => (
          <option key={code} value={code}>
            {row(code)}
          </option>
        ))}
      </optgroup>
    </select>
  );
}
