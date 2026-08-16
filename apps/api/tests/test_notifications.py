"""Notification events: real source events, honest channel status, ownership
isolation."""

from fastapi.testclient import TestClient

from app.api.emergency import _emergency_limiter, _sharing_limiter
from app.main import app
from app.reports.limiter import MemoryRateLimiter
from app.safety import MemoryContactStore, MemoryEmergencyStore, MemoryNotificationStore
from app.safety.contacts import get_contacts_store
from app.safety.notifications import get_notification_store
from app.safety.sessions import get_sessions_store

CLIENT_A = "a" * 32
CLIENT_B = "b" * 32


def make_client() -> TestClient:
    app.dependency_overrides = {}
    sessions = MemoryEmergencyStore()
    notifications = MemoryNotificationStore()
    emergency_limiter = MemoryRateLimiter(10, 3600)
    sharing_limiter = MemoryRateLimiter(60, 3600)
    app.dependency_overrides[get_contacts_store] = lambda: MemoryContactStore()
    app.dependency_overrides[get_sessions_store] = lambda: sessions
    app.dependency_overrides[get_notification_store] = lambda: notifications
    app.dependency_overrides[_emergency_limiter] = lambda: emergency_limiter
    app.dependency_overrides[_sharing_limiter] = lambda: sharing_limiter
    return TestClient(app)


def _headers(cid: str) -> dict[str, str]:
    return {"X-Client-Id": cid}


def test_notifications_require_client_id() -> None:
    client = make_client()
    assert client.get("/api/notifications").status_code == 401


def test_empty_notifications() -> None:
    client = make_client()
    resp = client.get("/api/notifications", headers=_headers(CLIENT_A))
    assert resp.status_code == 200
    assert resp.json()["notifications"] == []


def test_sos_start_and_end_create_events() -> None:
    client = make_client()
    payload = {"latitude": 28.61, "longitude": 77.20}
    created = client.post(
        "/api/emergency/sessions", json=payload, headers=_headers(CLIENT_A)
    ).json()
    events = client.get("/api/notifications", headers=_headers(CLIENT_A)).json()["notifications"]
    assert len(events) == 1
    assert events[0]["type"] == "sos_started"
    assert events[0]["status"] in ("queued", "no_channel")  # honest channel status
    assert events[0]["payload"]["session_id"] == created["session_id"]

    client.post(
        f"/api/emergency/sessions/{created['session_id']}/end",
        json={"reason": "safe"},
        headers=_headers(CLIENT_A),
    )
    events = client.get("/api/notifications", headers=_headers(CLIENT_A)).json()["notifications"]
    assert [e["type"] for e in events] == ["sos_ended", "sos_started"]


def test_sharing_start_stop_create_events() -> None:
    client = make_client()
    sharing = client.post(
        "/api/location-sharing", json={"ttl_s": 600}, headers=_headers(CLIENT_A)
    ).json()
    client.post(f"/api/location-sharing/{sharing['session_id']}/stop", headers=_headers(CLIENT_A))
    types = [
        e["type"]
        for e in client.get("/api/notifications", headers=_headers(CLIENT_A)).json()["notifications"]
    ]
    assert types == ["location_sharing_stopped", "location_sharing_started"]


def test_notifications_isolated_between_clients() -> None:
    client = make_client()
    client.post(
        "/api/emergency/sessions",
        json={"latitude": 28.61, "longitude": 77.20},
        headers=_headers(CLIENT_A),
    )
    assert client.get("/api/notifications", headers=_headers(CLIENT_B)).json()["notifications"] == []


def test_notification_limit_applied() -> None:
    client = make_client()
    for i in range(5):
        sharing = client.post(
            "/api/location-sharing", json={"ttl_s": 60}, headers=_headers(CLIENT_A)
        ).json()
        client.post(f"/api/location-sharing/{sharing['session_id']}/stop", headers=_headers(CLIENT_A))
    events = client.get(
        "/api/notifications?limit=3", headers=_headers(CLIENT_A)
    ).json()["notifications"]
    assert len(events) == 3


def test_telegram_channel_requires_both_credentials() -> None:
    """Without token AND chat id, delivery must stay honest: no_channel."""
    from app.notify import telegram_configured

    assert telegram_configured() is False


def test_telegram_unconfigured_status_is_no_channel() -> None:
    """Even when the channel is set to telegram, no credentials must never
    claim queued/sent delivery."""
    from app.config import settings
    from app.safety.notifications import expected_notify_status

    original = settings.notify_channel
    settings.notify_channel = "telegram"
    try:
        assert expected_notify_status() == "no_channel"
    finally:
        settings.notify_channel = original


def test_sms_channel_is_queued_not_sent() -> None:
    """sms has no live provider in this deployment: queued is the honest
    ceiling — never 'sent'."""
    from app.config import settings
    from app.safety.notifications import expected_notify_status

    original = settings.notify_channel
    settings.notify_channel = "sms"
    try:
        assert expected_notify_status() == "queued"
    finally:
        settings.notify_channel = original
