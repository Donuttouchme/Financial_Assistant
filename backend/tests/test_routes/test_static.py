def test_app_starts_when_frontend_dist_missing(client):
    # tests run from backend/ where ../frontend/dist does not exist;
    # the static mount should be skipped silently.
    response = client.get("/api/health")
    assert response.status_code == 200


def test_unknown_api_path_still_404s(client):
    response = client.get("/api/nope")
    assert response.status_code == 404
