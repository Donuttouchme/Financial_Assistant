"""Supported currency codes.

This is the canonical list of ISO 4217 codes the app understands. It exactly
mirrors frankfurter.app's supported set — every code here must round-trip
through `GET https://api.frankfurter.app/latest?from=<code>`.
"""

SUPPORTED_CURRENCIES: frozenset[str] = frozenset({
    "AUD", "BGN", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK",
    "EUR", "GBP", "HKD", "HUF", "IDR", "ILS", "INR", "ISK",
    "JPY", "KRW", "MXN", "MYR", "NOK", "NZD", "PHP", "PLN",
    "RON", "SEK", "SGD", "THB", "TRY", "USD", "ZAR",
})

MOST_USED: tuple[str, ...] = ("EUR", "HUF", "USD", "CHF", "GBP")
