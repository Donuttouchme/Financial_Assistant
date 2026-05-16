from datetime import date
from decimal import Decimal


def test_fx_status_empty(client):
    resp = client.get("/api/fx/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["latest_date"] is None
    assert body["source"] == "frankfurter.dev"
    assert body["is_fresh"] is False


def test_fx_status_with_today_row(client, db_session):
    from app.models.fx_rate import FxRate
    db_session.add(
        FxRate(currency="USD", date=date.today(), rate_to_eur=Decimal("1.08"))
    )
    db_session.commit()

    resp = client.get("/api/fx/status")
    body = resp.json()
    assert body["latest_date"] == date.today().isoformat()
    assert body["is_fresh"] is True


def test_fx_refresh_succeeds(client, monkeypatch):
    async def stub(*args, **kwargs):
        return (date.today(), 31)

    from app.services import fx_service
    monkeypatch.setattr(fx_service, "refresh_today", stub)

    resp = client.post("/api/fx/refresh")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["currencies_updated"] == 31


def test_fx_refresh_failure_reports_not_ok(client, monkeypatch):
    async def stub(*args, **kwargs):
        return (None, 0)

    from app.services import fx_service
    monkeypatch.setattr(fx_service, "refresh_today", stub)

    resp = client.post("/api/fx/refresh")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
