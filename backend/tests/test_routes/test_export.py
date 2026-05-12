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
    assert body[0] == "date,category,description,amount"
    assert body[1] == "2026-05-10,Groceries,Milk,12.34"


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
