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
