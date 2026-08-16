from fastapi.testclient import TestClient

from app.main import app, cors_origins_list

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


def test_cors_allows_configured_origin() -> None:
    resp = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_rejects_other_origin() -> None:
    resp = client.get("/health", headers={"Origin": "http://evil.example.com"})
    assert resp.headers.get("access-control-allow-origin") is None


def test_cors_origins_list_parses_comma_separated() -> None:
    assert cors_origins_list("http://a, http://b ,,http://c") == [
        "http://a",
        "http://b",
        "http://c",
    ]
    assert cors_origins_list("") == []
