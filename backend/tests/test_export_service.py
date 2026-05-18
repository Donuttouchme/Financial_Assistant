import csv
import io
from datetime import date
from decimal import Decimal

import pytest

from app.services import category_service, export_service, transaction_service


def test_export_csv_writes_expected_header_and_rows(db_session):
    groceries = category_service.create_category(db_session, user_id=1, name="Groceries")
    rent = category_service.create_category(db_session, user_id=1, name="Rent")
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("12.34"), tx_date=date(2026, 5, 3),
        category_id=groceries.id, description="Milk",
    )
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("500.00"), tx_date=date(2026, 5, 1),
        category_id=rent.id, description="May rent",
    )

    csv_bytes = export_service.export_transactions_csv(db_session, user_id=1, month="2026-05")
    csv_text = csv_bytes.decode("utf-8-sig")  # strips BOM if present

    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert rows[0] == ["date", "amount", "currency", "category", "description", "base_amount", "base_currency"]
    # rows ordered date desc — Milk (2026-05-03) first, Rent (2026-05-01) second
    assert rows[1][0] == "2026-05-03"
    assert rows[1][2] == "CHF"          # default currency
    assert rows[1][3] == "Groceries"
    assert rows[1][4] == "Milk"
    assert rows[1][5] == "12.34"        # base_amount same currency → same value
    assert rows[1][6] == "CHF"          # base_currency
    assert rows[2][0] == "2026-05-01"
    assert rows[2][3] == "Rent"
    assert rows[2][4] == "May rent"


def test_export_csv_returns_header_only_when_no_transactions(db_session):
    csv_bytes = export_service.export_transactions_csv(db_session, user_id=1, month="2026-05")
    csv_text = csv_bytes.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert rows == [["date", "amount", "currency", "category", "description", "base_amount", "base_currency"]]


def test_export_starts_with_utf8_bom_and_preserves_unicode(db_session):
    cat = category_service.create_category(db_session, user_id=1, name="Groceries")
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("9.90"), tx_date=date(2026, 5, 3),
        category_id=cat.id, description="COOP Zürich",
    )

    out = export_service.export_transactions_csv(db_session, user_id=1, month="2026-05")
    assert isinstance(out, bytes), "CSV export should return bytes so the BOM is preserved"
    assert out.startswith(b"\xef\xbb\xbf"), "CSV export should start with UTF-8 BOM for Excel"
    assert "Zürich" in out.decode("utf-8-sig")


def test_export_neutralises_formula_injection_in_description(db_session):
    cat = category_service.create_category(db_session, user_id=1, name="Groceries")
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("1.00"), tx_date=date(2026, 5, 3),
        category_id=cat.id, description="=cmd|'/c calc'!A1",
    )

    out = export_service.export_transactions_csv(db_session, user_id=1, month="2026-05")
    text = out.decode("utf-8-sig")

    assert "'=cmd" in text, "leading '=' in description should be prefixed with a single quote"
    # No raw row should start with `=` — i.e. no line break followed by `=cmd`
    assert "\n=cmd" not in text
    assert ",=cmd" not in text  # no unquoted injection survives at column boundary either


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@"])
def test_export_neutralises_all_injection_prefixes(db_session, prefix):
    cat = category_service.create_category(db_session, user_id=1, name="Groceries")
    payload = f"{prefix}HYPERLINK(\"http://evil\")"
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("1.00"), tx_date=date(2026, 5, 3),
        category_id=cat.id, description=payload,
    )

    out = export_service.export_transactions_csv(db_session, user_id=1, month="2026-05")
    text = out.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    # Description column is index 4
    assert rows[1][4] == f"'{payload}", (
        f"cell starting with {prefix!r} should be prefixed with single-quote, got {rows[1][4]!r}"
    )


def test_export_does_not_quote_safe_descriptions(db_session):
    """Neutralisation must not over-trigger: leading letters, digits, spaces are safe."""
    cat = category_service.create_category(db_session, user_id=1, name="Groceries")
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("1.00"), tx_date=date(2026, 5, 3),
        category_id=cat.id, description="Milk and eggs",
    )

    out = export_service.export_transactions_csv(db_session, user_id=1, month="2026-05")
    text = out.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    assert rows[1][4] == "Milk and eggs"  # untouched
