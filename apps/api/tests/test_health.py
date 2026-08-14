from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "env" in body


def test_unknown_route_returns_404() -> None:
    resp = client.get("/does-not-exist")
    assert resp.status_code == 404
