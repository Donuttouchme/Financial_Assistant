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
