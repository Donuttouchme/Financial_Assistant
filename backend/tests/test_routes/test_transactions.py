from datetime import date
from decimal import Decimal


def test_transaction_read_has_base_amount_same_currency(client, db_session):
    from app.models.category import Category
    from app.services import settings_service

    settings_service.set_base_currency(db_session, "CHF")
    cat = Category(user_id=1, name="Groceries", kind="expense")
    db_session.add(cat)
    db_session.commit()

    resp = client.post(
        "/api/transactions",
        json={
            "amount": "12.50",
            "date": "2026-05-14",
            "category_id": cat.id,
            "description": "lunch",
            "currency": "CHF",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["currency"] == "CHF"
    assert body["base_amount"] == "12.50"


def test_transaction_read_base_amount_converts(client, db_session):
    from app.models.category import Category
    from app.models.fx_rate import FxRate
    from app.services import settings_service

    settings_service.set_base_currency(db_session, "CHF")
    cat = Category(user_id=1, name="Groceries", kind="expense")
    db_session.add(cat)
    # rate_to_eur(CHF) = 0.96 means "1 EUR = 0.96 CHF" (frankfurter convention).
    # 100 EUR -> CHF = 100 * 0.96 = 96.00.
    db_session.add(FxRate(currency="EUR", date=date(2026, 5, 14), rate_to_eur=Decimal("1.0")))
    db_session.add(FxRate(currency="CHF", date=date(2026, 5, 14), rate_to_eur=Decimal("0.96")))
    db_session.commit()

    resp = client.post(
        "/api/transactions",
        json={
            "amount": "100.00",
            "date": "2026-05-14",
            "category_id": cat.id,
            "description": "x",
            "currency": "EUR",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["currency"] == "EUR"
    assert Decimal(body["base_amount"]).quantize(Decimal("0.01")) == Decimal("96.00")


def test_transaction_read_base_amount_none_when_missing_rate(client, db_session):
    from app.models.category import Category
    from app.services import settings_service

    settings_service.set_base_currency(db_session, "CHF")
    cat = Category(user_id=1, name="Groceries", kind="expense")
    db_session.add(cat)
    db_session.commit()

    resp = client.post(
        "/api/transactions",
        json={
            "amount": "100.00",
            "date": "2026-05-14",
            "category_id": cat.id,
            "description": "x",
            "currency": "EUR",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["base_amount"] is None


def test_create_transaction_returns_201(client):
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    response = client.post(
        "/api/transactions",
        json={
            "amount": "12.34",
            "date": "2026-05-10",
            "category_id": cat_id,
            "description": "Milk",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == "12.34"
    assert body["date"] == "2026-05-10"
    assert body["description"] == "Milk"
    assert body["is_recurring"] is False


def test_create_recurring_transaction_seeds_schedule(client, db_session):
    from app.services import recurring_service
    cat_id = client.post("/api/categories", json={"name": "Rent"}).json()["id"]
    client.post(
        "/api/transactions",
        json={
            "amount": "500.00",
            "date": "2026-05-01",
            "category_id": cat_id,
            "description": "Rent",
            "is_recurring": True,
        },
    )
    schedules = recurring_service.list_schedules(db_session, user_id=1)
    assert len(schedules) == 1
    assert schedules[0].next_occurrence_date.isoformat() == "2026-06-01"


def test_create_transaction_rejects_unknown_category(client):
    response = client.post(
        "/api/transactions",
        json={"amount": "5", "date": "2026-05-10", "category_id": 999, "description": ""},
    )
    assert response.status_code == 404


def test_create_transaction_rejects_zero_amount(client):
    cat_id = client.post("/api/categories", json={"name": "Misc"}).json()["id"]
    response = client.post(
        "/api/transactions",
        json={"amount": "0", "date": "2026-05-10", "category_id": cat_id, "description": ""},
    )
    assert response.status_code == 422


def test_list_transactions_filters_by_month_and_category(client):
    g = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    r = client.post("/api/categories", json={"name": "Rent"}).json()["id"]
    client.post("/api/transactions", json={"amount": "1", "date": "2026-04-30", "category_id": g, "description": "old"})
    client.post("/api/transactions", json={"amount": "5", "date": "2026-05-03", "category_id": g, "description": "food"})
    client.post("/api/transactions", json={"amount": "500", "date": "2026-05-01", "category_id": r, "description": "rent"})

    response = client.get("/api/transactions", params={"month": "2026-05"})
    assert response.status_code == 200
    descs = [t["description"] for t in response.json()]
    assert sorted(descs) == ["food", "rent"]

    only_rent = client.get("/api/transactions", params={"month": "2026-05", "category_id": r}).json()
    assert [t["description"] for t in only_rent] == ["rent"]


def test_update_transaction_returns_200_with_new_values(client):
    cat_id = client.post("/api/categories", json={"name": "Misc"}).json()["id"]
    tx_id = client.post(
        "/api/transactions",
        json={"amount": "5", "date": "2026-05-01", "category_id": cat_id, "description": "old"},
    ).json()["id"]

    response = client.put(
        f"/api/transactions/{tx_id}",
        json={"amount": "9.99", "description": "new"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["amount"] == "9.99"
    assert body["description"] == "new"
    assert body["date"] == "2026-05-01"


def test_update_unknown_transaction_returns_404(client):
    response = client.put("/api/transactions/9999", json={"amount": "1"})
    assert response.status_code == 404


def test_delete_transaction_returns_204(client):
    cat_id = client.post("/api/categories", json={"name": "Misc"}).json()["id"]
    tx_id = client.post(
        "/api/transactions",
        json={"amount": "5", "date": "2026-05-01", "category_id": cat_id, "description": ""},
    ).json()["id"]

    response = client.delete(f"/api/transactions/{tx_id}")
    assert response.status_code == 204

    assert client.get("/api/transactions").json() == []


def test_search_endpoint_returns_enriched_matches(client):
    cat = client.post("/api/categories", json={"name": "Food"}).json()["id"]
    client.post("/api/transactions", json={
        "amount": "10", "date": "2026-01-05", "category_id": cat,
        "description": "Lunch", "currency": "CHF",
    })
    client.post("/api/transactions", json={
        "amount": "20", "date": "2026-05-05", "category_id": cat,
        "description": "Dinner", "currency": "CHF",
    })

    resp = client.get("/api/transactions/search", params={"q": "lun"})
    assert resp.status_code == 200
    body = resp.json()
    assert [t["description"] for t in body] == ["Lunch"]
    assert "base_amount" in body[0]


def test_search_endpoint_short_query_returns_empty(client):
    resp = client.get("/api/transactions/search", params={"q": "a"})
    assert resp.status_code == 200
    assert resp.json() == []
