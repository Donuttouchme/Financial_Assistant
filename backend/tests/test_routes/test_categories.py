from datetime import date
from decimal import Decimal

from app.services import transaction_service


def test_create_category_returns_201_with_payload(client):
    response = client.post("/api/categories", json={"name": "Groceries"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Groceries"
    assert "id" in body


def test_list_categories_returns_all_users_categories(client):
    client.post("/api/categories", json={"name": "Groceries"})
    client.post("/api/categories", json={"name": "Rent"})

    response = client.get("/api/categories")
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert sorted(names) == ["Groceries", "Rent"]


def test_create_duplicate_category_returns_400(client):
    client.post("/api/categories", json={"name": "Groceries"})
    response = client.post("/api/categories", json={"name": "Groceries"})
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_category_rejects_empty_name(client):
    response = client.post("/api/categories", json={"name": ""})
    assert response.status_code == 422


def test_delete_category_returns_204(client):
    cat_id = client.post("/api/categories", json={"name": "Misc"}).json()["id"]
    response = client.delete(f"/api/categories/{cat_id}")
    assert response.status_code == 204

    listed = client.get("/api/categories").json()
    assert listed == []


def test_delete_unknown_category_returns_404(client):
    response = client.delete("/api/categories/9999")
    assert response.status_code == 404


def test_delete_category_referenced_by_transaction_returns_409(client, db_session):
    cat_id = client.post("/api/categories", json={"name": "Groceries"}).json()["id"]
    transaction_service.create_transaction(
        db_session, user_id=1, amount=Decimal("5"), tx_date=date(2026, 5, 1),
        category_id=cat_id, description="x",
    )
    response = client.delete(f"/api/categories/{cat_id}")
    assert response.status_code == 409
    assert "in use" in response.json()["detail"].lower()


def test_create_category_returns_kind_default_expense(client):
    body = client.post("/api/categories", json={"name": "Groceries"}).json()
    assert body["kind"] == "expense"


def test_create_category_with_income_kind(client):
    body = client.post(
        "/api/categories", json={"name": "Salary", "kind": "income"}
    ).json()
    assert body["kind"] == "income"


def test_create_category_rejects_invalid_kind(client):
    response = client.post(
        "/api/categories", json={"name": "Bad", "kind": "loan"}
    )
    assert response.status_code == 422


def test_list_categories_exposes_kind(client):
    client.post("/api/categories", json={"name": "Salary", "kind": "income"})
    client.post("/api/categories", json={"name": "Rent"})  # default expense
    rows = client.get("/api/categories").json()
    by_name = {c["name"]: c["kind"] for c in rows}
    assert by_name == {"Salary": "income", "Rent": "expense"}


def test_post_savings_category_with_target(client):
    r = client.post(
        "/api/categories",
        json={
            "name": "Vacation 2027",
            "kind": "savings",
            "target_amount": "3000.00",
            "target_date": "2027-06-30",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["kind"] == "savings"
    assert body["target_amount"] == "3000.00"
    assert body["target_date"] == "2027-06-30"


def test_post_savings_category_without_target(client):
    r = client.post(
        "/api/categories",
        json={"name": "Pillar 3a", "kind": "savings"},
    )
    assert r.status_code == 201
    assert r.json()["target_amount"] is None
    assert r.json()["target_date"] is None


def test_post_target_on_expense_returns_400(client):
    r = client.post(
        "/api/categories",
        json={
            "name": "Groceries",
            "kind": "expense",
            "target_amount": "100.00",
        },
    )
    assert r.status_code == 400
