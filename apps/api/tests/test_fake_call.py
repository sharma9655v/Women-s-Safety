"""Fake call (Feature Group T): schedule a simulated incoming call.

Covers the scheduled_at contract: the schema accepts an optional ring time
and defaults to now when omitted (regression for the 500 the endpoint
previously raised because scheduled_at was never part of the payload).
"""

from fastapi.testclient import TestClient

from app.main import app
from app.reports.limiter import MemoryRateLimiter
from app.safety import MemoryFakeCallStore, get_fake_call_store

CLIENT_A = "a" * 32


def make_client(*, limit: int = 10) -> TestClient:
    from app.api.fake_call import _fake_call_limiter

    app.dependency_overrides = {}
    calls = MemoryFakeCallStore()
    limiter = MemoryRateLimiter(limit, 3600)
    app.dependency_overrides[get_fake_call_store] = lambda: calls
    app.dependency_overrides[_fake_call_limiter] = lambda: limiter
    return TestClient(app)


def _headers(cid: str) -> dict[str, str]:
    return {"X-Client-Id": cid}


def test_fake_call_requires_client_id() -> None:
    client = make_client()
    resp = client.post("/api/fake-call", json={"caller_name": "Mom"})
    assert resp.status_code == 401


def test_create_fake_call_without_scheduled_at_defaults_to_now() -> None:
    client = make_client()
    resp = client.post(
        "/api/fake-call",
        json={"caller_name": "Mom", "caller_number": "9876543210"},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"]
    assert body["caller_name"] == "Mom"
    assert body["status"] == "SCHEDULED"
    assert body["scheduled_at"]  # not empty: defaulted to now
    assert body["scheduled_at"].endswith("+00:00")


def test_create_fake_call_with_scheduled_at() -> None:
    client = make_client()
    resp = client.post(
        "/api/fake-call",
        json={
            "caller_name": "Dad",
            "caller_number": "9123456780",
            "scheduled_at": "2026-08-16T12:00:00+00:00",
        },
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 201
    assert resp.json()["scheduled_at"] == "2026-08-16T12:00:00+00:00"


def test_get_fake_call_status_scoped_to_owner() -> None:
    client = make_client()
    created = client.post(
        "/api/fake-call", json={"caller_name": "Mom"}, headers=_headers(CLIENT_A)
    ).json()
    call_id = created["id"]
    resp = client.get(f"/api/fake-call/{call_id}", headers=_headers(CLIENT_A))
    assert resp.status_code == 200
    assert resp.json()["caller_name"] == "Mom"


def test_foreign_client_cannot_read_call() -> None:
    client = make_client()
    created = client.post(
        "/api/fake-call", json={"caller_name": "Mom"}, headers=_headers(CLIENT_A)
    ).json()
    resp = client.get(f"/api/fake-call/{created['id']}", headers=_headers("b" * 32))
    assert resp.status_code == 404


def test_validation() -> None:
    client = make_client()
    assert (
        client.post(
            "/api/fake-call", json={"caller_name": ""}, headers=_headers(CLIENT_A)
        ).status_code
        == 422
    )


def test_rate_limited() -> None:
    client = make_client(limit=2)
    for _ in range(2):
        assert (
            client.post(
                "/api/fake-call", json={"caller_name": "Mom"}, headers=_headers(CLIENT_A)
            ).status_code
            == 201
        )
    assert (
        client.post(
            "/api/fake-call", json={"caller_name": "Mom"}, headers=_headers(CLIENT_A)
        ).status_code
        == 429
    )
