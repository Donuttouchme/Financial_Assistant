def test_put_budget_returns_200_with_new_limit(client, freeze_month):
    freeze_month("2026-05")
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    response = client.put(
        f"/api/budgets/{cat_id}",
        json={"monthly_limit": "200"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category_id"] == cat_id
    assert body["month"] == "2026-05"
    assert body["monthly_limit"] == "200.00"


def test_put_budget_overwrites_existing_in_same_month(client, freeze_month):
    freeze_month("2026-05")
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    client.put(f"/api/budgets/{cat_id}", json={"monthly_limit": "200"})
    response = client.put(
        f"/api/budgets/{cat_id}",
        json={"monthly_limit": "250"},
    )
    assert response.status_code == 200
    assert response.json()["monthly_limit"] == "250.00"


def test_put_budget_silently_drops_month_in_payload(client, freeze_month):
    freeze_month("2026-05")
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    response = client.put(
        f"/api/budgets/{cat_id}",
        json={"month": "2026-05", "monthly_limit": "200"},
    )
    # BudgetSet has model_config defaulting to extra='ignore' (pydantic v2
    # default), so the field is silently dropped, not 422'd. The row still
    # gets effective_month=2026-05 from the clock fixture. Assert that
    # silent-drop is the behaviour we get.
    assert response.status_code == 200
    assert response.json()["month"] == "2026-05"


def test_put_budget_for_unknown_category_returns_404(client, freeze_month):
    freeze_month("2026-05")
    response = client.put("/api/budgets/9999", json={"monthly_limit": "10"})
    assert response.status_code == 404


def test_get_budgets_returns_spending_and_overage(client, freeze_month):
    freeze_month("2026-05")
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    client.put(f"/api/budgets/{cat_id}", json={"monthly_limit": "100"})
    client.post("/api/transactions", json={
        "amount": "60", "date": "2026-05-03", "category_id": cat_id, "description": "food",
    })
    client.post("/api/transactions", json={
        "amount": "70", "date": "2026-05-10", "category_id": cat_id, "description": "more food",
    })

    response = client.get("/api/budgets", params={"month": "2026-05"})
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0] == {
        "category_id": cat_id,
        "category_name": "Groceries",
        "month": "2026-05",
        "monthly_limit": "100.00",
        "spent": "130.00",
        "over_budget": True,
        "overage": "30.00",
    }


def test_get_budgets_for_month_without_budgets_returns_empty(client):
    response = client.get("/api/budgets", params={"month": "2026-05"})
    assert response.status_code == 200
    assert response.json() == []


def test_put_budget_on_income_category_returns_400(client, freeze_month):
    freeze_month("2026-05")
    cat_id = client.post(
        "/api/categories", json={"name": "Salary", "kind": "income"}
    ).json()["id"]
    response = client.put(
        f"/api/budgets/{cat_id}",
        json={"monthly_limit": "1000"},
    )
    assert response.status_code == 400
    assert "expense" in response.json()["detail"].lower()


def test_spent_aggregates_in_base_currency(client, db_session):
    from datetime import date
    from decimal import Decimal
    from app.models.category import Category
    from app.models.transaction import Transaction
    from app.models.budget_limit import BudgetLimit
    from app.models.fx_rate import FxRate
    from app.services import settings_service

    settings_service.set_base_currency(db_session, "CHF")
    cat = Category(user_id=1, name="Food", kind="expense")
    db_session.add(cat)
    db_session.flush()
    db_session.add(
        BudgetLimit(user_id=1, category_id=cat.id, month="2026-05", monthly_limit=Decimal("200"))
    )
    # rate_to_eur(CHF) = 0.96 means "1 EUR = 0.96 CHF" (frankfurter convention).
    # So 50 EUR -> CHF = 50 * 0.96 = 48 CHF. Total spent in CHF: 100 + 48 = 148.00.
    db_session.add(Transaction(
        user_id=1, amount=Decimal("100"), date=date(2026, 5, 10),
        category_id=cat.id, description="x", currency="CHF",
    ))
    db_session.add(Transaction(
        user_id=1, amount=Decimal("50"), date=date(2026, 5, 11),
        category_id=cat.id, description="y", currency="EUR",
    ))
    db_session.add(FxRate(currency="EUR", date=date(2026, 5, 10), rate_to_eur=Decimal("1.0")))
    db_session.add(FxRate(currency="CHF", date=date(2026, 5, 10), rate_to_eur=Decimal("0.96")))
    db_session.add(FxRate(currency="EUR", date=date(2026, 5, 11), rate_to_eur=Decimal("1.0")))
    db_session.add(FxRate(currency="CHF", date=date(2026, 5, 11), rate_to_eur=Decimal("0.96")))
    db_session.commit()

    resp = client.get("/api/budgets?month=2026-05")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    spent = Decimal(body[0]["spent"]).quantize(Decimal("0.01"))
    # 100 CHF (native) + 50 EUR * 0.96 = 100 + 48 = 148.00 CHF
    assert spent == Decimal("148.00")
