def test_create_and_list_preset(client):
    r = client.post(
        "/api/import-presets",
        json={"name": "UBS", "config": {"delimiter": ";"}},
    )
    assert r.status_code == 201
    pid = r.json()["id"]

    r = client.get("/api/import-presets")
    names = [p["name"] for p in r.json()]
    assert "UBS" in names
    assert any(p["id"] == pid for p in r.json())


def test_update_preset(client):
    pid = client.post(
        "/api/import-presets",
        json={"name": "UBS", "config": {}},
    ).json()["id"]
    r = client.put(
        f"/api/import-presets/{pid}",
        json={"name": "UBS-2", "config": {"a": 1}},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "UBS-2"
    assert r.json()["config"] == {"a": 1}


def test_delete_preset(client):
    pid = client.post(
        "/api/import-presets",
        json={"name": "UBS", "config": {}},
    ).json()["id"]
    r = client.delete(f"/api/import-presets/{pid}")
    assert r.status_code == 204
    assert client.get("/api/import-presets").json() == []


def test_create_duplicate_name_returns_400(client):
    client.post("/api/import-presets", json={"name": "UBS", "config": {}})
    r = client.post("/api/import-presets", json={"name": "UBS", "config": {}})
    assert r.status_code == 400
