import { formatMoney, parseMoneyInput } from "@/lib/money";

/** @deprecated Use formatMoney(amount, currency) from @/lib/money. */
export function formatChf(value: string | number): string {
  return formatMoney(value, "CHF");
}

/** @deprecated Use parseMoneyInput from @/lib/money. */
export function parseChfInput(raw: string): string {
  return parseMoneyInput(raw);
}
