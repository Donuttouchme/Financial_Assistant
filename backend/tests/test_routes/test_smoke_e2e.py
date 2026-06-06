def test_full_user_flow(client, freeze_month):
    freeze_month("2026-05")
    # 1. Health
    assert client.get("/api/health").json() == {"status": "ok"}

    # 2. Create categories
    groceries = client.post("/api/categories", json={"name": "Groceries"}).json()
    rent = client.post("/api/categories", json={"name": "Rent"}).json()
    assert {c["name"] for c in client.get("/api/categories").json()} == {"Groceries", "Rent"}

    # 3. Create transactions (one recurring)
    client.post("/api/transactions", json={
        "amount": "12.34", "date": "2026-05-10",
        "category_id": groceries["id"], "description": "Milk",
    })
    client.post("/api/transactions", json={
        "amount": "500.00", "date": "2026-05-01",
        "category_id": rent["id"], "description": "Rent", "is_recurring": True,
    })

    listed = client.get("/api/transactions", params={"month": "2026-05"}).json()
    assert len(listed) == 2

    # 4. Set a budget that gets blown (effective_month server-stamped to 2026-05)
    client.put(f"/api/budgets/{groceries['id']}",
               json={"monthly_limit": "10"})
    budgets = client.get("/api/budgets", params={"month": "2026-05"}).json()
    assert budgets[0]["over_budget"] is True

    # 5. Export
    csv_resp = client.get("/api/export/csv", params={"month": "2026-05"})
    assert csv_resp.status_code == 200
    assert "Milk" in csv_resp.text
    assert "Rent" in csv_resp.text

    # 6. Delete one transaction
    tx_id = listed[0]["id"]
    assert client.delete(f"/api/transactions/{tx_id}").status_code == 204
    assert len(client.get("/api/transactions", params={"month": "2026-05"}).json()) == 1


def test_cors_preflight_allows_localhost_3000(client):
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
