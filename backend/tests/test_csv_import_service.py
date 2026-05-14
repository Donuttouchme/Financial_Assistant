from datetime import date
from decimal import Decimal

from app.schemas.csv_import import CsvColumnMapping, CsvImportConfig
from app.services.csv_import_service import parse_csv


def _cfg(**over):
    base = dict(
        delimiter=";",
        decimal_sep=".",
        thousands_sep="",
        date_format="%Y-%m-%d",
        skip_header_rows=0,
        has_header=False,
        amount_format="signed",
        sign_convention="negative_is_expense",
        cols=CsvColumnMapping(date=0, description=1, amount=2),
    )
    base.update(over)
    return CsvImportConfig(**base)


def test_parse_minimal_signed_csv():
    text = "2026-05-13;COOP Zürich;-45.30\n2026-05-13;Salary;+5200\n"
    rows = parse_csv(text, _cfg())
    assert len(rows) == 2
    assert rows[0].date == date(2026, 5, 13)
    assert rows[0].description == "COOP Zürich"
    assert rows[0].amount == Decimal("-45.30")
    assert rows[0].kind_hint == "expense"
    assert rows[1].amount == Decimal("5200")
    assert rows[1].kind_hint == "income"
    assert all(r.errors == [] for r in rows)


def test_parse_swiss_decimals_and_thousands():
    text = "2026-05-13;Salary;5'200,50\n"
    cfg = _cfg(decimal_sep=",", thousands_sep="'")
    rows = parse_csv(text, cfg)
    assert rows[0].amount == Decimal("5200.50")


def test_parse_skips_header_rows():
    text = "preamble1\npreamble2\nDate;Desc;Amount\n2026-05-13;X;-10\n"
    cfg = _cfg(skip_header_rows=2, has_header=True)
    rows = parse_csv(text, cfg)
    assert len(rows) == 1
    assert rows[0].description == "X"


def test_parse_debit_credit_layout():
    text = "2026-05-13;COOP;45.30;\n2026-05-13;Salary;;5200\n"
    cfg = _cfg(
        amount_format="debit_credit",
        cols=CsvColumnMapping(date=0, description=1, debit=2, credit=3),
    )
    rows = parse_csv(text, cfg)
    assert rows[0].amount == Decimal("-45.30")
    assert rows[0].kind_hint == "expense"
    assert rows[1].amount == Decimal("5200")
    assert rows[1].kind_hint == "income"


def test_parse_row_with_bad_date_flags_error_but_does_not_raise():
    text = "not-a-date;X;10\n"
    rows = parse_csv(text, _cfg())
    assert rows[0].errors
    assert "date" in rows[0].errors[0].lower()


def test_parse_european_date_format():
    text = "13.05.2026;X;10\n"
    cfg = _cfg(date_format="%d.%m.%Y")
    rows = parse_csv(text, cfg)
    assert rows[0].date == date(2026, 5, 13)
    assert rows[0].errors == []
