def test_export_csv_returns_csv_content_type_and_header(client):
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    client.post("/api/transactions", json={
        "amount": "12.34", "date": "2026-05-10", "category_id": cat_id, "description": "Milk",
    })

    response = client.get("/api/export/csv", params={"month": "2026-05"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert "2026-05" in response.headers["content-disposition"]

    body = response.text.splitlines()
    assert body[0] == "date,amount,currency,category,description,base_amount,base_currency"
    # data row: date, amount, currency, category, description, base_amount, base_currency
    parts = body[1].split(",")
    assert parts[0] == "2026-05-10"
    assert parts[1] == "12.34"
    assert parts[3] == "Groceries"
    assert parts[4] == "Milk"


def test_export_csv_without_month_returns_all(client):
    cat_id = client.post("/api/categories", json={"name": "Misc"}).json()["id"]
    client.post("/api/transactions", json={
        "amount": "1.00", "date": "2026-04-30", "category_id": cat_id, "description": "april",
    })
    client.post("/api/transactions", json={
        "amount": "2.00", "date": "2026-05-01", "category_id": cat_id, "description": "may",
    })

    response = client.get("/api/export/csv")
    assert response.status_code == 200
    lines = response.text.splitlines()
    assert len(lines) == 3  # header + 2 rows


def test_export_csv_rejects_bad_month(client):
    response = client.get("/api/export/csv", params={"month": "bad"})
    assert response.status_code == 422


def test_export_includes_currency_columns(client, db_session):
    from datetime import date
    from decimal import Decimal
    from app.models.category import Category
    from app.models.transaction import Transaction
    from app.models.fx_rate import FxRate
    from app.services import settings_service

    settings_service.set_base_currency(db_session, "CHF")
    cat = Category(user_id=1, name="Food", kind="expense")
    db_session.add(cat)
    db_session.flush()
    db_session.add(Transaction(
        user_id=1, amount=Decimal("12.50"), date=date(2026, 5, 14),
        category_id=cat.id, description="lunch", currency="EUR",
    ))
    db_session.add(FxRate(currency="EUR", date=date(2026, 5, 14), rate_to_eur=Decimal("1.0")))
    db_session.add(FxRate(currency="CHF", date=date(2026, 5, 14), rate_to_eur=Decimal("0.96")))
    db_session.commit()

    resp = client.get("/api/export/csv", params={"month": "2026-05"})
    assert resp.status_code == 200
    text = resp.text
    header = text.splitlines()[0].split(",")
    for col in ("date", "amount", "currency", "category", "description", "base_amount", "base_currency"):
        assert col in header, f"missing {col} in {header!r}"

    data_row = text.splitlines()[1].split(",")
    idx_currency = header.index("currency")
    idx_base = header.index("base_amount")
    idx_base_ccy = header.index("base_currency")
    assert data_row[idx_currency] == "EUR"
    assert data_row[idx_base_ccy] == "CHF"
    # 12.50 EUR * 1.0 / 0.96 = 13.02 CHF
    assert Decimal(data_row[idx_base]).quantize(Decimal("0.01")) == Decimal("13.02")
