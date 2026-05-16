import { SUPPORTED_CURRENCIES, isSupportedCurrency } from "@/lib/currencies";

export const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  JPY: "¥",
  HUF: "Ft",
  CHF: "CHF",
  AUD: "A$",
  CAD: "CA$",
  NZD: "NZ$",
  HKD: "HK$",
  SGD: "S$",
  ZAR: "R",
  SEK: "kr",
  NOK: "kr",
  DKK: "kr",
  PLN: "zł",
  CZK: "Kč",
  RON: "lei",
  BGN: "лв",
  TRY: "₺",
  INR: "₹",
  KRW: "₩",
  THB: "฿",
  IDR: "Rp",
  PHP: "₱",
  MYR: "RM",
  MXN: "Mex$",
  BRL: "R$",
  CNY: "¥",
  ILS: "₪",
  ISK: "kr",
};

export const LOCALE_FOR: Record<string, string> = {
  USD: "en-US",
  EUR: "de-DE",
  GBP: "en-GB",
  JPY: "ja-JP",
  HUF: "hu-HU",
  CHF: "de-CH",
  AUD: "en-AU",
  CAD: "en-CA",
  NZD: "en-NZ",
  HKD: "en-HK",
  SGD: "en-SG",
  ZAR: "en-ZA",
  SEK: "sv-SE",
  NOK: "nb-NO",
  DKK: "da-DK",
  PLN: "pl-PL",
  CZK: "cs-CZ",
  RON: "ro-RO",
  BGN: "bg-BG",
  TRY: "tr-TR",
  INR: "en-IN",
  KRW: "ko-KR",
  THB: "th-TH",
  IDR: "id-ID",
  PHP: "en-PH",
  MYR: "ms-MY",
  MXN: "es-MX",
  BRL: "pt-BR",
  CNY: "zh-CN",
  ILS: "he-IL",
  ISK: "is-IS",
};

// Currencies whose minor units are not used in practice — format with 0 decimals.
const ZERO_DECIMAL_CURRENCIES = new Set(["HUF", "JPY", "KRW", "ISK", "IDR"]);

export function formatMoney(value: string | number, currency: string): string {
  const n = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(n)) throw new Error(`formatMoney: not a number: ${value}`);
  if (!isSupportedCurrency(currency)) {
    return `${n.toFixed(2)} ${currency}`;
  }
  const locale = LOCALE_FOR[currency] ?? "en-US";
  const zeroDecimal = ZERO_DECIMAL_CURRENCIES.has(currency);
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: zeroDecimal ? 0 : 2,
    maximumFractionDigits: zeroDecimal ? 0 : 2,
  }).format(n);
}

export function parseMoneyInput(raw: string): string {
  // Strip thousand separators: apostrophe (U+0027), right single quote (U+2019),
  // non-breaking space (U+00A0), narrow no-break space (U+202F), regular whitespace.
  // Expects "." as the decimal separator (HTML <input type="number"> always
  // produces this regardless of user locale). Comma-as-decimal input like
  // "1234,56" is rejected by the regex; if we ever accept free-text amount
  // entry we'll need to handle that explicitly.
  const cleaned = raw.replace(/['’  \s]/g, "");
  if (!/^-?\d+(\.\d+)?$/.test(cleaned)) {
    throw new Error(`parseMoneyInput: not numeric: ${raw}`);
  }
  return cleaned;
}

export function getCurrencySymbol(code: string): string {
  return CURRENCY_SYMBOLS[code] ?? code;
}

export type { SupportedCurrency } from "@/lib/currencies";
export { SUPPORTED_CURRENCIES, isSupportedCurrency };
