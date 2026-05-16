import csv
import io
from datetime import date
from decimal import Decimal

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

    csv_text = export_service.export_transactions_csv(db_session, user_id=1, month="2026-05")

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
    csv_text = export_service.export_transactions_csv(db_session, user_id=1, month="2026-05")
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert rows == [["date", "amount", "currency", "category", "description", "base_amount", "base_currency"]]
