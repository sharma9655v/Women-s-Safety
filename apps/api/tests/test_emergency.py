"""Emergency SOS + location sharing API: lifecycle, consent, expiry,
duplicate activation, ownership isolation."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.reports.limiter import MemoryRateLimiter
from app.safety import MemoryContactStore, MemoryEmergencyStore, MemoryNotificationStore
from app.safety.contacts import get_contacts_store
from app.safety.notifications import get_notification_store
from app.safety.sessions import get_sessions_store

CLIENT_A = "a" * 32
CLIENT_B = "b" * 32

FIXED_NOW = datetime(2026, 8, 15, 10, 0, tzinfo=UTC)


def make_client(
    *, emergency_limit: int = 10, sharing_limit: int = 60, sharing_update_limit: int = 600
) -> TestClient:
    from app.api.emergency import (
        _emergency_limiter,
        _sharing_limiter,
        _sharing_update_limiter,
    )

    app.dependency_overrides = {}
    contacts = MemoryContactStore()
    sessions = MemoryEmergencyStore()
    notifications = MemoryNotificationStore()
    emergency_limiter = MemoryRateLimiter(emergency_limit, 3600)
    sharing_limiter = MemoryRateLimiter(sharing_limit, 3600)
    sharing_update_limiter = MemoryRateLimiter(sharing_update_limit, 3600)
    app.dependency_overrides[get_contacts_store] = lambda: contacts
    app.dependency_overrides[get_sessions_store] = lambda: sessions
    app.dependency_overrides[get_notification_store] = lambda: notifications
    app.dependency_overrides[_emergency_limiter] = lambda: emergency_limiter
    app.dependency_overrides[_sharing_limiter] = lambda: sharing_limiter
    app.dependency_overrides[_sharing_update_limiter] = lambda: sharing_update_limiter
    return TestClient(app)


def _headers(cid: str) -> dict[str, str]:
    return {"X-Client-Id": cid}


def _sos(lat: float = 28.6139, lon: float = 77.2090) -> dict[str, object]:
    return {"latitude": lat, "longitude": lon, "notified_contact_ids": [1, 2]}


# --- SOS lifecycle -----------------------------------------------------------


def test_sos_requires_client_id() -> None:
    client = make_client()
    assert client.post("/api/emergency/sessions", json=_sos()).status_code == 401
    assert client.get("/api/emergency/sessions/active").status_code == 401


def test_no_active_session_before_activation() -> None:
    client = make_client()
    resp = client.get("/api/emergency/sessions/active", headers=_headers(CLIENT_A))
    assert resp.status_code == 200
    assert resp.json() is None


def test_activate_emergency_session() -> None:
    client = make_client()
    resp = client.post("/api/emergency/sessions", json=_sos(), headers=_headers(CLIENT_A))
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "ACTIVE"
    assert body["latitude"] == 28.6139
    assert body["notified_contact_ids"] == [1, 2]
    assert body["notify_status"] in ("queued", "no_channel")
    active = client.get("/api/emergency/sessions/active", headers=_headers(CLIENT_A)).json()
    assert active["session_id"] == body["session_id"]


def test_duplicate_active_session_conflict() -> None:
    client = make_client()
    client.post("/api/emergency/sessions", json=_sos(), headers=_headers(CLIENT_A))
    resp = client.post("/api/emergency/sessions", json=_sos(), headers=_headers(CLIENT_A))
    assert resp.status_code == 409


def test_second_client_can_have_own_session() -> None:
    client = make_client()
    client.post("/api/emergency/sessions", json=_sos(), headers=_headers(CLIENT_A))
    resp = client.post("/api/emergency/sessions", json=_sos(), headers=_headers(CLIENT_B))
    assert resp.status_code == 201


def test_update_emergency_location() -> None:
    client = make_client()
    created = client.post("/api/emergency/sessions", json=_sos(), headers=_headers(CLIENT_A)).json()
    resp = client.post(
        f"/api/emergency/sessions/{created['session_id']}/location",
        json={"latitude": 28.62, "longitude": 77.22},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["latitude"] == 28.62
    assert body["last_known_at"] is not None


def test_end_emergency_session() -> None:
    client = make_client()
    created = client.post("/api/emergency/sessions", json=_sos(), headers=_headers(CLIENT_A)).json()
    resp = client.post(
        f"/api/emergency/sessions/{created['session_id']}/end",
        json={"reason": "safe"},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ENDED"
    assert resp.json()["end_reason"] == "safe"
    assert client.get("/api/emergency/sessions/active", headers=_headers(CLIENT_A)).json() is None


def test_ending_ended_session_404() -> None:
    client = make_client()
    created = client.post("/api/emergency/sessions", json=_sos(), headers=_headers(CLIENT_A)).json()
    client.post(
        f"/api/emergency/sessions/{created['session_id']}/end",
        json={"reason": "safe"},
        headers=_headers(CLIENT_A),
    )
    resp = client.post(
        f"/api/emergency/sessions/{created['session_id']}/end",
        json={"reason": "again"},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 404


def test_cross_client_session_404() -> None:
    client = make_client()
    created = client.post("/api/emergency/sessions", json=_sos(), headers=_headers(CLIENT_A)).json()
    resp = client.post(
        f"/api/emergency/sessions/{created['session_id']}/end",
        json={"reason": "safe"},
        headers=_headers(CLIENT_B),
    )
    assert resp.status_code == 404
    resp = client.post(
        f"/api/emergency/sessions/{created['session_id']}/location",
        json={"latitude": 1.0, "longitude": 1.0},
        headers=_headers(CLIENT_B),
    )
    assert resp.status_code == 404


def test_sos_rate_limited() -> None:
    client = make_client(emergency_limit=2)
    client.post("/api/emergency/sessions", json=_sos(), headers=_headers(CLIENT_A))
    client.post("/api/emergency/sessions", json=_sos(), headers=_headers(CLIENT_A))
    resp = client.post("/api/emergency/sessions", json=_sos(), headers=_headers(CLIENT_A))
    assert resp.status_code == 429


# --- location sharing --------------------------------------------------------


def test_sharing_requires_explicit_start() -> None:
    client = make_client()
    assert client.get("/api/location-sharing/active", headers=_headers(CLIENT_A)).json() is None


def test_start_and_query_sharing() -> None:
    client = make_client()
    resp = client.post(
        "/api/location-sharing",
        json={"kind": "EMERGENCY", "ttl_s": 1800, "recipient_ids": [1, 2]},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "ACTIVE"
    assert body["expires_at"] > datetime.now(UTC).isoformat()
    active = client.get("/api/location-sharing/active", headers=_headers(CLIENT_A)).json()
    assert active["session_id"] == body["session_id"]
    assert active["recipient_ids"] == [1, 2]


def test_sharing_linked_to_emergency_session() -> None:
    client = make_client()
    emergency = client.post(
        "/api/emergency/sessions", json=_sos(), headers=_headers(CLIENT_A)
    ).json()
    resp = client.post(
        "/api/location-sharing",
        json={
            "kind": "EMERGENCY",
            "owner_session": emergency["session_id"],
            "ttl_s": 600,
        },
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 201


def test_sharing_with_unknown_owner_session_404() -> None:
    client = make_client()
    resp = client.post(
        "/api/location-sharing",
        json={"kind": "EMERGENCY", "owner_session": "does-not-exist", "ttl_s": 600},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 404


def test_update_sharing_location() -> None:
    client = make_client()
    sharing = client.post(
        "/api/location-sharing", json={"ttl_s": 600}, headers=_headers(CLIENT_A)
    ).json()
    resp = client.post(
        f"/api/location-sharing/{sharing['session_id']}/location",
        json={"latitude": 28.65, "longitude": 77.19},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 200
    assert resp.json()["latitude"] == 28.65


def test_location_updates_are_not_starved_by_session_creation_limit() -> None:
    # GPS fixes arrive continuously; 100 rapid updates must all succeed even
    # though the session-creation limit is only 60/hour.
    client = make_client()
    sharing = client.post(
        "/api/location-sharing", json={"ttl_s": 600}, headers=_headers(CLIENT_A)
    ).json()
    for i in range(100):
        resp = client.post(
            f"/api/location-sharing/{sharing['session_id']}/location",
            json={"latitude": 28.6 + i / 1000, "longitude": 77.2},
            headers=_headers(CLIENT_A),
        )
        assert resp.status_code == 200, f"update {i} failed"


def test_location_updates_are_rate_limited_when_flooded() -> None:
    client = make_client(sharing_update_limit=3)
    sharing = client.post(
        "/api/location-sharing", json={"ttl_s": 600}, headers=_headers(CLIENT_A)
    ).json()
    for _ in range(3):
        resp = client.post(
            f"/api/location-sharing/{sharing['session_id']}/location",
            json={"latitude": 28.6, "longitude": 77.2},
            headers=_headers(CLIENT_A),
        )
        assert resp.status_code == 200
    resp = client.post(
        f"/api/location-sharing/{sharing['session_id']}/location",
        json={"latitude": 28.6, "longitude": 77.2},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 429


def test_stop_sharing() -> None:
    client = make_client()
    sharing = client.post(
        "/api/location-sharing", json={"ttl_s": 600}, headers=_headers(CLIENT_A)
    ).json()
    resp = client.post(
        f"/api/location-sharing/{sharing['session_id']}/stop", headers=_headers(CLIENT_A)
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "STOPPED"
    assert client.get("/api/location-sharing/active", headers=_headers(CLIENT_A)).json() is None


def test_sharing_expires_after_ttl(monkeypatch) -> None:
    import app.safety.sessions as sessions_module

    client = make_client()
    fake = {"now": FIXED_NOW}
    monkeypatch.setattr(sessions_module, "_now", lambda: fake["now"])
    sharing = client.post(
        "/api/location-sharing", json={"ttl_s": 600}, headers=_headers(CLIENT_A)
    ).json()
    assert sharing["status"] == "ACTIVE"
    fake["now"] = FIXED_NOW + timedelta(seconds=601)
    active = client.get("/api/location-sharing/active", headers=_headers(CLIENT_A)).json()
    assert active["status"] == "EXPIRED"
    # expired sessions cannot be updated
    resp = client.post(
        f"/api/location-sharing/{sharing['session_id']}/location",
        json={"latitude": 1.0, "longitude": 1.0},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 404


def test_cross_client_sharing_404() -> None:
    client = make_client()
    sharing = client.post(
        "/api/location-sharing", json={"ttl_s": 600}, headers=_headers(CLIENT_A)
    ).json()
    assert (
        client.get(
            f"/api/location-sharing/{sharing['session_id']}", headers=_headers(CLIENT_B)
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/location-sharing/{sharing['session_id']}/stop", headers=_headers(CLIENT_B)
        ).status_code
        == 404
    )
