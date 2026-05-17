from decimal import Decimal


def test_get_settings_returns_default_chf(client):
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    assert resp.json() == {"base_currency": "CHF"}


def test_patch_base_currency_changes_value(client):
    resp = client.patch("/api/settings/base_currency", json={"base_currency": "HUF"})
    assert resp.status_code == 200
    assert resp.json() == {"base_currency": "HUF"}

    follow = client.get("/api/settings")
    assert follow.json() == {"base_currency": "HUF"}


def test_patch_base_currency_rejects_unknown(client):
    # Pydantic accepts the length, then service raises ValueError -> 400
    resp = client.patch("/api/settings/base_currency", json={"base_currency": "ZZZ"})
    assert resp.status_code == 400


def test_preview_base_currency_lists_affected_budgets(client, db_session):
    from datetime import date
    from app.models.category import Category
    from app.models.budget_limit import BudgetLimit
    from app.models.fx_rate import FxRate

    cat = Category(user_id=1, name="Food", kind="expense")
    db_session.add(cat)
    db_session.flush()
    db_session.add(
        BudgetLimit(user_id=1, category_id=cat.id, month="2026-05", monthly_limit=Decimal("200"))
    )

    # Set up FX rates so preview can convert at today's rate
    db_session.add(FxRate(currency="EUR", date=date.today(), rate_to_eur=Decimal("1.0")))
    db_session.add(FxRate(currency="CHF", date=date.today(), rate_to_eur=Decimal("0.96")))
    db_session.commit()

    resp = client.post(
        "/api/settings/base_currency/preview",
        json={"base_currency": "EUR"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["new_base"] == "EUR"
    assert body["old_base"] == "CHF"
    budgets = body["budgets"]
    assert len(budgets) == 1
    assert budgets[0]["category_name"] == "Food"
    assert budgets[0]["old_amount"] == "200.00"
    # rate_to_eur(CHF) = 0.96 means "1 EUR = 0.96 CHF" (frankfurter convention).
    # 200 CHF -> EUR = 200 * 1.0 / 0.96 = 208.33 EUR.
    assert Decimal(budgets[0]["new_amount"]).quantize(Decimal("0.01")) == Decimal("208.33")


def test_preview_base_currency_returns_409_when_rates_missing(client, db_session):
    from decimal import Decimal
    from app.models.category import Category
    from app.models.budget_limit import BudgetLimit

    # Set up a budget but NO fx_rates rows. The preview must fail to convert.
    cat = Category(user_id=1, name="Food", kind="expense")
    db_session.add(cat)
    db_session.flush()
    db_session.add(
        BudgetLimit(user_id=1, category_id=cat.id, month="2026-05", monthly_limit=Decimal("200"))
    )
    db_session.commit()

    resp = client.post(
        "/api/settings/base_currency/preview",
        json={"base_currency": "EUR"},
    )
    assert resp.status_code == 409
    assert "FX rate" in resp.json()["detail"]


def test_commit_base_currency_returns_409_when_rates_missing(client, db_session):
    from decimal import Decimal
    from app.models.category import Category
    from app.models.budget_limit import BudgetLimit

    cat = Category(user_id=1, name="Food", kind="expense")
    db_session.add(cat)
    db_session.flush()
    db_session.add(
        BudgetLimit(user_id=1, category_id=cat.id, month="2026-05", monthly_limit=Decimal("200"))
    )
    db_session.commit()

    resp = client.patch(
        "/api/settings/base_currency",
        json={"base_currency": "EUR"},
    )
    assert resp.status_code == 409
