def test_put_budget_returns_200_with_new_limit(client):
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    response = client.put(
        f"/api/budgets/{cat_id}",
        json={"month": "2026-05", "monthly_limit": "200"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category_id"] == cat_id
    assert body["month"] == "2026-05"
    assert body["monthly_limit"] == "200.00"


def test_put_budget_overwrites_existing(client):
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    client.put(f"/api/budgets/{cat_id}", json={"month": "2026-05", "monthly_limit": "200"})
    response = client.put(
        f"/api/budgets/{cat_id}",
        json={"month": "2026-05", "monthly_limit": "250"},
    )
    assert response.status_code == 200
    assert response.json()["monthly_limit"] == "250.00"


def test_put_budget_for_unknown_category_returns_404(client):
    response = client.put(
        "/api/budgets/9999", json={"month": "2026-05", "monthly_limit": "10"}
    )
    assert response.status_code == 404


def test_put_budget_rejects_bad_month(client):
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    response = client.put(
        f"/api/budgets/{cat_id}", json={"month": "2026/05", "monthly_limit": "10"}
    )
    assert response.status_code == 422


def test_get_budgets_returns_spending_and_overage(client):
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    client.put(f"/api/budgets/{cat_id}", json={"month": "2026-05", "monthly_limit": "100"})
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
