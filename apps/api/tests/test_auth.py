"""Device session token flow (Group D auth)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.auth import _auth_limiter
from app.config import settings
from app.main import app
from app.reports.limiter import MemoryRateLimiter

client = TestClient(app)

CID = "a1b2c3d4e5f60718293a4b5c6d7e8f90"

# Isolate from the Redis-backed limiter (shared with the live API when Redis
# is reachable): the fixed test client id would otherwise 429 after a few runs.
app.dependency_overrides[_auth_limiter] = lambda: MemoryRateLimiter(100, 60)


def _device_token(cid: str = CID) -> str:
    resp = client.post("/api/auth/device", json={"client_id": cid})
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


def test_issue_device_token() -> None:
    token = _device_token()
    assert len(token) >= 32


def test_token_grants_private_endpoint_access() -> None:
    token = _device_token()
    resp = client.get(
        "/api/contacts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"contacts": []}


def test_invalid_token_rejected() -> None:
    resp = client.get(
        "/api/contacts",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 401


def test_no_auth_rejected_without_legacy_fallback(monkeypatch) -> None:
    monkeypatch.setattr(settings, "allow_legacy_client_id", False)
    resp = client.get("/api/contacts")
    assert resp.status_code == 401
    resp = client.get("/api/contacts", headers={"X-Client-Id": CID})
    assert resp.status_code == 401


def test_legacy_header_still_works_when_enabled() -> None:
    resp = client.get("/api/contacts", headers={"X-Client-Id": CID})
    assert resp.status_code == 200


def test_revoke_token() -> None:
    token = _device_token()
    resp = client.post("/api/auth/revoke", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    resp = client.get(
        "/api/contacts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


def test_token_is_client_scoped() -> None:
    _ = _device_token()
    other = _device_token("9f0e1d2c3b4a5968778695a4b3c2d1e0f")
    resp = client.get(
        "/api/contacts",
        headers={"Authorization": f"Bearer {other}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"contacts": []}


def test_bad_client_id_rejected() -> None:
    resp = client.post("/api/auth/device", json={"client_id": "short"})
    assert resp.status_code == 400
