import time

from app import idle


def test_heartbeat_returns_ok(client):
    response = client.post("/api/heartbeat")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_heartbeat_does_not_require_auth(client):
    # No auth override on this route — the dependency override on get_current_user_id
    # in conftest is harmless because heartbeat doesn't depend on it.
    response = client.post("/api/heartbeat")
    assert response.status_code == 200


def test_request_through_middleware_updates_last_activity(client):
    # Force the timestamp back by 10 s so the bump is observable.
    idle._last_activity = time.monotonic() - 10.0
    before = idle._last_activity
    response = client.post("/api/heartbeat")
    assert response.status_code == 200
    assert idle._last_activity > before
