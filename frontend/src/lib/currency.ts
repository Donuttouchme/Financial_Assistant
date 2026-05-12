const _formatter = new Intl.NumberFormat("de-CH", {
  style: "currency",
  currency: "CHF",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatChf(value: string | number): string {
  const n = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(n)) throw new Error(`formatChf: not a number: ${value}`);
  return _formatter.format(n);
}

export function parseChfInput(raw: string): string {
  // Strip: regular apostrophe (U+0027), right single quotation mark (U+2019),
  // non-breaking space (U+00A0), and any other whitespace.
  const cleaned = raw.replace(/['’ \s]/g, "");
  if (!/^-?\d+(\.\d+)?$/.test(cleaned)) {
    throw new Error(`parseChfInput: not numeric: ${raw}`);
  }
  return cleaned;
}
