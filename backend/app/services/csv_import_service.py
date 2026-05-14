import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import StringIO

from app.schemas.csv_import import CsvImportConfig, ParsedRow


def _normalize_number(raw: str, decimal_sep: str, thousands_sep: str) -> Decimal:
    s = raw.strip()
    if not s:
        raise InvalidOperation("empty")
    if thousands_sep:
        s = s.replace(thousands_sep, "")
    if decimal_sep != ".":
        s = s.replace(decimal_sep, ".")
    s = s.replace("+", "")
    return Decimal(s)


def parse_csv(text: str, config: CsvImportConfig) -> list[ParsedRow]:
    reader = csv.reader(StringIO(text), delimiter=config.delimiter)
    all_rows = list(reader)

    start = config.skip_header_rows + (1 if config.has_header else 0)
    data = all_rows[start:]

    out: list[ParsedRow] = []
    cols = config.cols

    for idx, raw in enumerate(data):
        row = ParsedRow(row_index=idx)

        try:
            row.date = datetime.strptime(raw[cols.date].strip(), config.date_format).date()
        except (ValueError, IndexError) as exc:
            row.errors.append(f"bad date: {exc}")

        try:
            row.description = raw[cols.description].strip()
        except IndexError:
            row.errors.append("missing description column")

        if config.amount_format == "signed":
            if cols.amount is None:
                row.errors.append("config: amount column not set")
            else:
                try:
                    n = _normalize_number(
                        raw[cols.amount], config.decimal_sep, config.thousands_sep
                    )
                    row.amount = n
                except (InvalidOperation, IndexError) as exc:
                    row.errors.append(f"bad amount: {exc}")
        else:
            if cols.debit is None or cols.credit is None:
                row.errors.append("config: debit/credit columns not set")
            else:
                try:
                    d_raw = raw[cols.debit].strip() if cols.debit < len(raw) else ""
                    c_raw = raw[cols.credit].strip() if cols.credit < len(raw) else ""
                    if d_raw and c_raw:
                        row.errors.append("both debit and credit populated")
                    elif d_raw:
                        n = _normalize_number(d_raw, config.decimal_sep, config.thousands_sep)
                        row.amount = -abs(n)
                    elif c_raw:
                        n = _normalize_number(c_raw, config.decimal_sep, config.thousands_sep)
                        row.amount = abs(n)
                    else:
                        row.errors.append("debit and credit both empty")
                except (InvalidOperation, IndexError) as exc:
                    row.errors.append(f"bad amount: {exc}")

        if row.amount is not None:
            if config.sign_convention == "negative_is_expense":
                row.kind_hint = "expense" if row.amount < 0 else "income"
            else:
                row.kind_hint = "income" if row.amount < 0 else "expense"

        out.append(row)

    return out
