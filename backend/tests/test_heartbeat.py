def test_heartbeat_returns_ok(client):
    response = client.post("/api/heartbeat")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_heartbeat_does_not_require_auth(client):
    # No auth override on this route — the dependency override on get_current_user_id
    # in conftest is harmless because heartbeat doesn't depend on it.
    response = client.post("/api/heartbeat")
    assert response.status_code == 200
