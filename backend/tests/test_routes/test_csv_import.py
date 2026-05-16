def _seed_category(client, name="Imported", kind="expense"):
    return client.post("/api/categories", json={"name": name, "kind": kind}).json()


_BASE_CONFIG = {
    "delimiter": ";",
    "decimal_sep": ".",
    "thousands_sep": "",
    "date_format": "%Y-%m-%d",
    "skip_header_rows": 0,
    "has_header": False,
    "amount_format": "signed",
    "sign_convention": "negative_is_expense",
    "cols": {"date": 0, "description": 1, "amount": 2},
}


def test_preview_returns_parsed_rows(client):
    payload = {
        "file_content": "2026-05-13;COOP;-45.30\n2026-05-13;Salary;5200\n",
        "config": {
            "delimiter": ";",
            "decimal_sep": ".",
            "thousands_sep": "",
            "date_format": "%Y-%m-%d",
            "skip_header_rows": 0,
            "has_header": False,
            "amount_format": "signed",
            "sign_convention": "negative_is_expense",
            "cols": {"date": 0, "description": 1, "amount": 2},
        },
    }
    r = client.post("/api/import/preview", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert len(body["rows"]) == 2
    assert body["rows"][0]["kind_hint"] == "expense"
    assert body["rows"][1]["kind_hint"] == "income"


def test_preview_flags_dupes(client):
    cat = _seed_category(client)
    # Seed an existing transaction matching the first CSV row.
    client.post(
        "/api/transactions",
        json={
            "amount": "45.30",
            "date": "2026-05-13",
            "category_id": cat["id"],
            "description": "COOP",
        },
    )
    payload = {
        "file_content": "2026-05-13;COOP;-45.30\n2026-05-13;Salary;5200\n",
        "config": {
            "delimiter": ";",
            "decimal_sep": ".",
            "thousands_sep": "",
            "date_format": "%Y-%m-%d",
            "skip_header_rows": 0,
            "has_header": False,
            "amount_format": "signed",
            "sign_convention": "negative_is_expense",
            "cols": {"date": 0, "description": 1, "amount": 2},
        },
    }
    r = client.post("/api/import/preview", json=payload)
    body = r.json()
    assert body["rows"][0]["is_duplicate"] is True
    assert body["rows"][1]["is_duplicate"] is False


def test_commit_creates_only_selected_rows(client):
    cat = _seed_category(client)
    payload = {
        "file_content": "2026-05-13;COOP;-45.30\n2026-05-13;Salary;5200\n",
        "config": {
            "delimiter": ";",
            "decimal_sep": ".",
            "thousands_sep": "",
            "date_format": "%Y-%m-%d",
            "skip_header_rows": 0,
            "has_header": False,
            "amount_format": "signed",
            "sign_convention": "negative_is_expense",
            "cols": {"date": 0, "description": 1, "amount": 2},
        },
        "selections": [
            {"row_index": 1, "category_id": cat["id"], "is_recurring": False},
            # row_index 0 omitted -> skipped
        ],
    }
    r = client.post("/api/import/commit", json=payload)
    assert r.status_code == 200
    assert r.json() == {"imported": 1, "skipped": 1}

    txs = client.get("/api/transactions?month=2026-05").json()
    assert len(txs) == 1


def test_commit_with_default_currency(client):
    """Rows without a currency column inherit the file's default_currency."""
    cat = _seed_category(client, kind="income")
    payload = {
        "file_content": "2026-05-14;salary;5000\n",
        "config": {**_BASE_CONFIG},
        "selections": [
            {"row_index": 0, "category_id": cat["id"], "is_recurring": False},
        ],
        "default_currency": "EUR",
    }
    r = client.post("/api/import/commit", json=payload)
    assert r.status_code == 200
    assert r.json() == {"imported": 1, "skipped": 0}

    txs = client.get("/api/transactions?month=2026-05").json()
    assert len(txs) == 1
    assert txs[0]["currency"] == "EUR"


def test_commit_with_per_row_currency_column(client):
    """When a currency column is mapped, each row's currency overrides the default."""
    cat = _seed_category(client, kind="income")
    # CSV: date;desc;amount;currency  (col 3 = currency)
    payload = {
        "file_content": "2026-05-14;bonus;20.00;USD\n2026-05-14;gift;3.50;GBP\n",
        "config": {
            **_BASE_CONFIG,
            "cols": {"date": 0, "description": 1, "amount": 2, "currency": 3},
        },
        "selections": [
            {"row_index": 0, "category_id": cat["id"], "is_recurring": False},
            {"row_index": 1, "category_id": cat["id"], "is_recurring": False},
        ],
        "default_currency": "EUR",
    }
    r = client.post("/api/import/commit", json=payload)
    assert r.status_code == 200
    assert r.json() == {"imported": 2, "skipped": 0}

    txs = client.get("/api/transactions?month=2026-05").json()
    assert len(txs) == 2
    currencies = {tx["currency"] for tx in txs}
    assert currencies == {"USD", "GBP"}


def test_commit_with_config_default_currency(client):
    """default_currency on the config object is used as fallback when not set on the commit request."""
    cat = _seed_category(client, kind="income")
    payload = {
        "file_content": "2026-05-14;dividends;100\n",
        "config": {**_BASE_CONFIG, "default_currency": "CHF"},
        "selections": [
            {"row_index": 0, "category_id": cat["id"], "is_recurring": False},
        ],
    }
    r = client.post("/api/import/commit", json=payload)
    assert r.status_code == 200

    txs = client.get("/api/transactions?month=2026-05").json()
    assert len(txs) == 1
    assert txs[0]["currency"] == "CHF"


def test_commit_eager_fills_fx_rates_for_each_unique_date(client, monkeypatch):
    """commit_import should call fetch_rates_for_date once per unique row date."""
    from datetime import date
    from decimal import Decimal as _D
    from app.services import fx_service

    seen: list[date] = []

    async def stub_fetch(target):
        seen.append(target)
        return {"EUR": _D("1.0"), "USD": _D("1.08"), "CHF": _D("0.96"), "GBP": _D("0.85")}

    monkeypatch.setattr(fx_service, "fetch_rates_for_date", stub_fetch)

    cat = _seed_category(client, kind="income")
    # Two rows on 2026-05-14, one on 2026-05-15 — fetch_rates_for_date should
    # be called exactly twice (one per unique date) thanks to the set in
    # ensure_rates_for_dates.
    payload = {
        "file_content": (
            "2026-05-14;bonus;20.00\n"
            "2026-05-14;gift;3.50\n"
            "2026-05-15;tip;1.00\n"
        ),
        "config": {**_BASE_CONFIG},
        "selections": [
            {"row_index": 0, "category_id": cat["id"], "is_recurring": False},
            {"row_index": 1, "category_id": cat["id"], "is_recurring": False},
            {"row_index": 2, "category_id": cat["id"], "is_recurring": False},
        ],
        "default_currency": "USD",
    }
    r = client.post("/api/import/commit", json=payload)
    assert r.status_code == 200
    assert set(seen) == {date(2026, 5, 14), date(2026, 5, 15)}
