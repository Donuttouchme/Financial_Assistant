def _seed_category(client, name="Imported", kind="expense"):
    return client.post("/api/categories", json={"name": name, "kind": kind}).json()


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
