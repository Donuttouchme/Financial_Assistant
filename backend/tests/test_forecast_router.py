from datetime import date
from decimal import Decimal

from app.models.category import Category
from app.models.transaction import Transaction
from app.services import settings_service


def test_daily_cumulative_endpoint_returns_31_points(client, db_session):
    settings_service.set_base_currency(db_session, "EUR")
    food = Category(name="Food", kind="expense", user_id=1)
    db_session.add(food); db_session.commit()
    db_session.add(Transaction(
        user_id=1, category_id=food.id, amount=Decimal("10"),
        currency="EUR", date=date(2026, 5, 1), description="",
    ))
    db_session.commit()

    r = client.get("/api/forecast/daily-cumulative?month=2026-05")
    assert r.status_code == 200
    body = r.json()
    assert body["month"] == "2026-05"
    assert body["base_currency"] == "EUR"
    assert len(body["points"]) == 31
    assert "is_forecast" in body["points"][0]
    assert "cumulative" in body["points"][0]


def test_daily_cumulative_rejects_bad_month_pattern(client):
    r = client.get("/api/forecast/daily-cumulative?month=2026")
    assert r.status_code == 422


def test_daily_cumulative_category_filter(client, db_session):
    settings_service.set_base_currency(db_session, "EUR")
    food = Category(name="Food", kind="expense", user_id=1)
    fuel = Category(name="Fuel", kind="expense", user_id=1)
    db_session.add_all([food, fuel]); db_session.commit()
    db_session.add_all([
        Transaction(user_id=1, category_id=food.id, amount=Decimal("10"),
                    currency="EUR", date=date(2026, 5, 1), description=""),
        Transaction(user_id=1, category_id=fuel.id, amount=Decimal("99"),
                    currency="EUR", date=date(2026, 5, 1), description=""),
    ])
    db_session.commit()

    r = client.get(f"/api/forecast/daily-cumulative?month=2026-05&category_id={food.id}")
    assert r.status_code == 200
    last_real = r.json()["points"][0]  # day 1
    assert Decimal(last_real["cumulative"]) == Decimal("10")


def test_monthly_buckets_endpoint_3m_centered(client, db_session):
    settings_service.set_base_currency(db_session, "EUR")
    r = client.get("/api/forecast/monthly-buckets?horizon=3m&mode=centered")
    assert r.status_code == 200
    body = r.json()
    assert body["horizon"] == "3m"
    assert body["mode"] == "centered"
    assert len(body["points"]) == 3


def test_monthly_buckets_default_mode_is_centered(client, db_session):
    settings_service.set_base_currency(db_session, "EUR")
    r = client.get("/api/forecast/monthly-buckets?horizon=6m")
    assert r.status_code == 200
    assert r.json()["mode"] == "centered"


def test_monthly_buckets_rejects_bad_horizon(client):
    r = client.get("/api/forecast/monthly-buckets?horizon=99y")
    assert r.status_code == 422


def test_monthly_buckets_rejects_bad_mode(client):
    r = client.get("/api/forecast/monthly-buckets?horizon=3m&mode=sideways")
    assert r.status_code == 422
