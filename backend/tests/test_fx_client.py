from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.services import fx_service


@pytest.mark.asyncio
async def test_fetch_rates_for_date_parses_response(monkeypatch):
    sample = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2026-05-14",
        "rates": {"USD": 1.08, "GBP": 0.85, "HUF": 397.5, "CHF": 0.96},
    }

    async def fake_get(self, url, *args, **kwargs):
        request = httpx.Request("GET", url)
        return httpx.Response(200, json=sample, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    rates = await fx_service.fetch_rates_for_date(date(2026, 5, 14))
    assert rates["EUR"] == Decimal("1.0")  # base always 1
    assert rates["USD"] == Decimal("1.08")
    assert rates["HUF"] == Decimal("397.5")


@pytest.mark.asyncio
async def test_fetch_rates_raises_on_http_error(monkeypatch):
    async def fake_get(self, url, *args, **kwargs):
        request = httpx.Request("GET", url)
        return httpx.Response(503, request=request, text="upstream")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(fx_service.FxFetchError):
        await fx_service.fetch_rates_for_date(date(2026, 5, 14))


@pytest.mark.asyncio
async def test_fetch_rates_for_today_uses_latest_endpoint(monkeypatch):
    captured = {}

    async def fake_get(self, url, *args, **kwargs):
        captured["url"] = url
        request = httpx.Request("GET", url)
        return httpx.Response(
            200,
            json={"amount": 1.0, "base": "EUR", "date": "2026-05-15", "rates": {"USD": 1.08}},
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    await fx_service.fetch_rates_for_today()
    assert captured["url"].endswith("/latest")
