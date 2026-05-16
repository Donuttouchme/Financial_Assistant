import { CURRENCY_SYMBOLS } from "@/lib/money";
import {
  CURRENCY_NAMES,
  MOST_USED,
  SUPPORTED_CURRENCIES,
  isSupportedCurrency,
} from "@/lib/currencies";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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

function rowLabel(code: string): string {
  const symbol = CURRENCY_SYMBOLS[code] ?? code;
  const name = isSupportedCurrency(code) ? CURRENCY_NAMES[code] : code;
  return `${symbol}  ${code}  ${name}`;
}

export function CurrencySelect({ value, onChange, id, disabled, className, ...rest }: Props) {
  return (
    <Select value={value} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger
        id={id}
        aria-label={rest["aria-label"] ?? "Currency"}
        className={className}
      >
        <SelectValue placeholder="Select currency" />
      </SelectTrigger>
      <SelectContent>
        <SelectGroup>
          <SelectLabel>Most used</SelectLabel>
          {MOST_USED.map((code) => (
            <SelectItem key={code} value={code}>
              {rowLabel(code)}
            </SelectItem>
          ))}
        </SelectGroup>
        <SelectGroup>
          <SelectLabel>All currencies</SelectLabel>
          {OTHER_CURRENCIES.map((code) => (
            <SelectItem key={code} value={code}>
              {rowLabel(code)}
            </SelectItem>
          ))}
        </SelectGroup>
      </SelectContent>
    </Select>
  );
}
