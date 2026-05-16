export const SUPPORTED_CURRENCIES = [
  "AUD", "BGN", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK",
  "EUR", "GBP", "HKD", "HUF", "IDR", "ILS", "INR", "ISK",
  "JPY", "KRW", "MXN", "MYR", "NOK", "NZD", "PHP", "PLN",
  "RON", "SEK", "SGD", "THB", "TRY", "USD", "ZAR",
] as const;

export type SupportedCurrency = (typeof SUPPORTED_CURRENCIES)[number];

export const MOST_USED: readonly SupportedCurrency[] = [
  "EUR", "HUF", "USD", "CHF", "GBP",
] as const;

export function isSupportedCurrency(code: string): code is SupportedCurrency {
  return (SUPPORTED_CURRENCIES as readonly string[]).includes(code);
}

// Full coverage required — TypeScript enforces sync with SUPPORTED_CURRENCIES.
export const CURRENCY_NAMES: Record<SupportedCurrency, string> = {
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
