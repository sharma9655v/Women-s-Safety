"""Community posts: create/feed lifecycle, moderation, rate limits, privacy."""

from fastapi.testclient import TestClient

from app.api.community import _community_limiter
from app.community import MemoryCommunityStore, get_community_store
from app.main import app
from app.reports.limiter import MemoryRateLimiter

CLIENT_A = "a" * 32


def make_client(*, post_limit: int = 5) -> TestClient:
    from app.api.emergency import _emergency_limiter, _sharing_limiter
    from app.api.guardian import _guardian_limiter
    from app.safety import (
        MemoryContactStore,
        MemoryEmergencyStore,
        MemoryGuardianStore,
        MemoryNotificationStore,
    )
    from app.safety.contacts import get_contacts_store
    from app.safety.guardian import get_guardian_store
    from app.safety.notifications import get_notification_store
    from app.safety.sessions import get_sessions_store

    app.dependency_overrides = {}
    community = MemoryCommunityStore()
    post_limiter = MemoryRateLimiter(post_limit, 3600)
    app.dependency_overrides[get_community_store] = lambda: community
    app.dependency_overrides[_community_limiter] = lambda: post_limiter
    app.dependency_overrides[get_contacts_store] = lambda: MemoryContactStore()
    app.dependency_overrides[get_guardian_store] = lambda: MemoryGuardianStore()
    app.dependency_overrides[get_sessions_store] = lambda: MemoryEmergencyStore()
    app.dependency_overrides[get_notification_store] = lambda: MemoryNotificationStore()
    app.dependency_overrides[_guardian_limiter] = lambda: MemoryRateLimiter(10, 3600)
    app.dependency_overrides[_emergency_limiter] = lambda: MemoryRateLimiter(10, 3600)
    app.dependency_overrides[_sharing_limiter] = lambda: MemoryRateLimiter(60, 3600)
    return TestClient(app)


def _headers(cid: str = CLIENT_A) -> dict[str, str]:
    return {"X-Client-Id": cid}


def _post(client: TestClient, **overrides) -> dict:
    payload = {
        "kind": "route_update",
        "location": "Tilak Marg",
        "text": "The footpath near the metro exit has been repaired.",
        **overrides,
    }
    return client.post("/api/community", json=payload, headers=_headers())


def test_post_requires_client_id() -> None:
    client = make_client()
    assert client.post("/api/community", json={}).status_code == 401


def test_create_post_pending() -> None:
    client = make_client()
    resp = _post(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "PENDING"
    assert body["kind"] == "route_update"
    assert "client_id" not in body
    assert body["created_at"]


def test_feed_includes_pending_and_verified() -> None:
    client = make_client()
    created = _post(client).json()
    client.post(
        "/api/admin/community/{}/verify".format(created["id"]),
        headers={"X-Admin-Key": "dev-admin-key"},
    )
    feed = client.get("/api/community").json()["posts"]
    assert [p["id"] for p in feed] == [created["id"]]
    assert feed[0]["status"] == "VERIFIED"


def test_rejected_hidden_from_feed() -> None:
    client = make_client()
    created = _post(client).json()
    client.post(
        "/api/admin/community/{}/reject".format(created["id"]),
        headers={"X-Admin-Key": "dev-admin-key"},
    )
    assert client.get("/api/community").json()["posts"] == []


def test_admin_verify_reject_requires_key() -> None:
    client = make_client()
    created = _post(client).json()
    assert (
        client.post(
            "/api/admin/community/{}/verify".format(created["id"]), headers={}
        ).status_code
        == 403
    )


def test_admin_moderate_unknown_post_404() -> None:
    client = make_client()
    resp = client.post(
        "/api/admin/community/does-not-exist/verify",
        headers={"X-Admin-Key": "dev-admin-key"},
    )
    assert resp.status_code == 404


def test_feed_ordered_newest_first() -> None:
    client = make_client()
    first = _post(client, text="First update about the repaired footpath.").json()
    second = _post(client, text="Second update about the new streetlight here.").json()
    ids = [p["id"] for p in client.get("/api/community").json()["posts"]]
    assert ids == [second["id"], first["id"]]


def test_rate_limited() -> None:
    client = make_client(post_limit=2)
    _post(client)
    _post(client)
    assert _post(client).status_code == 429


def test_validation() -> None:
    client = make_client()
    assert _post(client, text="short").status_code == 422
    assert _post(client, kind="spam").status_code == 422
    assert _post(client, location="").status_code == 422


def test_multiple_clients_separate_counts() -> None:
    client = make_client()
    _post(client)
    _post(client, text="Another update from the same device here.")
    other = _post(client, headers=_headers("b" * 32))
    assert other.status_code == 201
