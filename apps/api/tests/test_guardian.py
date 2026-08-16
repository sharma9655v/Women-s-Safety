"""Guardian journeys: lifecycle, staged escalation, deviation detection,
exactly-once notifications, ownership isolation."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api.guardian import _guardian_limiter
from app.main import app
from app.reports.limiter import MemoryRateLimiter
from app.safety import (
    MemoryContactStore,
    MemoryEmergencyStore,
    MemoryGuardianStore,
    MemoryNotificationStore,
)
from app.safety.contacts import get_contacts_store
from app.safety.guardian import deviation_m, get_guardian_store
from app.safety.notifications import get_notification_store
from app.safety.sessions import get_sessions_store

CLIENT_A = "a" * 32
CLIENT_B = "b" * 32

FIXED_NOW = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)


def make_client(*, guardian_limit: int = 10) -> TestClient:
    from app.api.emergency import _emergency_limiter, _sharing_limiter

    app.dependency_overrides = {}
    guardian = MemoryGuardianStore()
    sessions = MemoryEmergencyStore()
    notifications = MemoryNotificationStore()
    guardian_limiter = MemoryRateLimiter(guardian_limit, 3600)
    emergency_limiter = MemoryRateLimiter(10, 3600)
    sharing_limiter = MemoryRateLimiter(60, 3600)
    app.dependency_overrides[get_contacts_store] = lambda: MemoryContactStore()
    app.dependency_overrides[get_guardian_store] = lambda: guardian
    app.dependency_overrides[get_sessions_store] = lambda: sessions
    app.dependency_overrides[get_notification_store] = lambda: notifications
    app.dependency_overrides[_guardian_limiter] = lambda: guardian_limiter
    app.dependency_overrides[_emergency_limiter] = lambda: emergency_limiter
    app.dependency_overrides[_sharing_limiter] = lambda: sharing_limiter
    return TestClient(app)


def _headers(cid: str) -> dict[str, str]:
    return {"X-Client-Id": cid}


def _create(client: TestClient, cid: str = CLIENT_A, **overrides) -> dict:
    payload = {
        "guardian_contact_ids": [1, 2],
        "expected_arrival_at": (FIXED_NOW + timedelta(minutes=30)).isoformat(),
        "checkin_grace_s": 300,
        **overrides,
    }
    resp = client.post("/api/guardian/sessions", json=payload, headers=_headers(cid))
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- lifecycle ---------------------------------------------------------------


def test_guardian_requires_client_id() -> None:
    client = make_client()
    assert client.post("/api/guardian/sessions", json={}).status_code == 401
    assert client.get("/api/guardian/sessions/active").status_code == 401


def test_create_and_read_active() -> None:
    client = make_client()
    body = _create(client)
    assert body["status"] == "ACTIVE"
    assert body["guardian_contact_ids"] == [1, 2]
    assert body["escalation_stage"] == 0
    active = client.get("/api/guardian/sessions/active", headers=_headers(CLIENT_A)).json()
    assert active["session_id"] == body["session_id"]
    assert active["checkin_deadline"] == body["checkin_deadline"]


def test_no_active_before_start() -> None:
    client = make_client()
    assert client.get("/api/guardian/sessions/active", headers=_headers(CLIENT_A)).json() is None


def test_duplicate_active_conflict() -> None:
    client = make_client()
    _create(client)
    resp = client.post(
        "/api/guardian/sessions",
        json={"guardian_contact_ids": [3]},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 409


def test_cross_client_404() -> None:
    client = make_client()
    body = _create(client)
    resp = client.get(f"/api/guardian/sessions/{body['session_id']}", headers=_headers(CLIENT_B))
    assert resp.status_code == 404
    resp = client.post(
        f"/api/guardian/sessions/{body['session_id']}/checkin", headers=_headers(CLIENT_B)
    )
    assert resp.status_code == 404
    resp = client.post(
        f"/api/guardian/sessions/{body['session_id']}/end",
        json={"reason": "cancelled"},
        headers=_headers(CLIENT_B),
    )
    assert resp.status_code == 404


def test_end_journey_completed() -> None:
    client = make_client()
    body = _create(client)
    resp = client.post(
        f"/api/guardian/sessions/{body['session_id']}/end",
        json={"reason": "arrived"},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"
    assert client.get("/api/guardian/sessions/active", headers=_headers(CLIENT_A)).json() is None


def test_end_cancelled() -> None:
    client = make_client()
    body = _create(client)
    resp = client.post(
        f"/api/guardian/sessions/{body['session_id']}/end",
        json={"reason": "cancelled"},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


def test_ending_ended_session_404() -> None:
    client = make_client()
    body = _create(client)
    client.post(
        f"/api/guardian/sessions/{body['session_id']}/end",
        json={"reason": "cancelled"},
        headers=_headers(CLIENT_A),
    )
    resp = client.post(
        f"/api/guardian/sessions/{body['session_id']}/end",
        json={"reason": "cancelled"},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 404


def test_guardian_rate_limited() -> None:
    client = make_client(guardian_limit=2)
    client.post(
        "/api/guardian/sessions",
        json={"guardian_contact_ids": [1]},
        headers=_headers(CLIENT_A),
    )
    client.post(
        "/api/guardian/sessions",
        json={"guardian_contact_ids": [1]},
        headers=_headers(CLIENT_A),
    )
    resp = client.post(
        "/api/guardian/sessions",
        json={"guardian_contact_ids": [1]},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 429


def test_invalid_geometry_rejected() -> None:
    client = make_client()
    resp = client.post(
        "/api/guardian/sessions",
        json={"planned_geometry": [[1.0, 2.0, 3.0]]},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 422


# --- check-ins + staged escalation -------------------------------------------


def test_checkin_resets_deadline(monkeypatch) -> None:
    import app.safety.guardian as guardian_module

    client = make_client()
    fake = {"now": FIXED_NOW}
    monkeypatch.setattr(guardian_module, "_now", lambda: fake["now"])
    body = _create(client)
    fake["now"] = FIXED_NOW + timedelta(minutes=35)  # past arrival+grace
    active = client.get("/api/guardian/sessions/active", headers=_headers(CLIENT_A)).json()
    assert active["escalation_stage"] == 1
    resp = client.post(
        f"/api/guardian/sessions/{body['session_id']}/checkin", headers=_headers(CLIENT_A)
    )
    assert resp.status_code == 200
    assert resp.json()["escalation_stage"] == 0
    assert resp.json()["last_checkin_at"] is not None
    # A check-in supersedes the (stale) expected arrival: the new deadline is
    # grace seconds after the check-in itself.
    new_deadline = resp.json()["checkin_deadline"]
    assert datetime.fromisoformat(new_deadline) == FIXED_NOW + timedelta(
        minutes=35, seconds=300
    )


def test_escalation_stage_1_then_2_exactly_once(monkeypatch) -> None:
    import app.safety.guardian as guardian_module

    client = make_client()
    fake = {"now": FIXED_NOW}
    monkeypatch.setattr(guardian_module, "_now", lambda: fake["now"])
    _create(client)

    # Before the deadline: no events.
    events = client.get("/api/notifications", headers=_headers(CLIENT_A)).json()["notifications"]
    types = [e["type"] for e in events]
    assert "checkin_missed" not in types
    assert "checkin_escalated" not in types

    # Stage 1: past arrival+grace.
    fake["now"] = FIXED_NOW + timedelta(minutes=35)
    active = client.get("/api/guardian/sessions/active", headers=_headers(CLIENT_A)).json()
    assert active["escalation_stage"] == 1
    types = [e["type"] for e in client.get(
        "/api/notifications", headers=_headers(CLIENT_A)
    ).json()["notifications"]]
    assert types.count("checkin_missed") == 1

    # Repeated reads do not re-emit.
    client.get("/api/guardian/sessions/active", headers=_headers(CLIENT_A))
    types = [e["type"] for e in client.get(
        "/api/notifications", headers=_headers(CLIENT_A)
    ).json()["notifications"]]
    assert types.count("checkin_missed") == 1

    # Stage 2: deadline (12:35) + escalation delay (15 min) = 12:50.
    fake["now"] = FIXED_NOW + timedelta(minutes=55)
    active = client.get("/api/guardian/sessions/active", headers=_headers(CLIENT_A)).json()
    assert active["escalation_stage"] == 2
    assert active["status"] == "ESCALATED"
    types = [e["type"] for e in client.get(
        "/api/notifications", headers=_headers(CLIENT_A)
    ).json()["notifications"]]
    assert types.count("checkin_escalated") == 1


def test_no_auto_sos_by_default(monkeypatch) -> None:
    import app.safety.guardian as guardian_module

    client = make_client()
    fake = {"now": FIXED_NOW}
    monkeypatch.setattr(guardian_module, "_now", lambda: fake["now"])
    _create(client)
    fake["now"] = FIXED_NOW + timedelta(minutes=55)
    client.get("/api/guardian/sessions/active", headers=_headers(CLIENT_A))
    assert client.get("/api/emergency/sessions/active", headers=_headers(CLIENT_A)).json() is None


# --- deviation ---------------------------------------------------------------


def test_deviation_m_math() -> None:
    # Straight east-west line through (77.0, 28.6) -> (77.1, 28.6).
    line = [(77.0, 28.6), (77.1, 28.6)]
    assert deviation_m(28.6, 77.05, line) < 100  # on the line: ~0
    # 0.01 deg latitude north ~= 1111 m; threshold default is 200 m.
    assert deviation_m(28.61, 77.05, line) > 800
    # Single point: distance to the point.
    assert deviation_m(28.6001, 77.05, [(77.05, 28.6)]) < 50


def test_deviation_detected_and_notified_once() -> None:
    client = make_client()
    body = _create(client, planned_geometry=[[77.0, 28.6], [77.1, 28.6]])
    resp = client.post(
        f"/api/guardian/sessions/{body['session_id']}/location",
        json={"latitude": 28.62, "longitude": 77.05},  # ~2.2 km off route
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 200
    assert resp.json()["deviation_detected"] is True
    assert resp.json()["first_deviation_at"] is not None
    types = [e["type"] for e in client.get(
        "/api/notifications", headers=_headers(CLIENT_A)
    ).json()["notifications"]]
    assert types.count("route_changed") == 1

    # Second update while still off-route: no duplicate notification.
    client.post(
        f"/api/guardian/sessions/{body['session_id']}/location",
        json={"latitude": 28.63, "longitude": 77.05},
        headers=_headers(CLIENT_A),
    )
    types = [e["type"] for e in client.get(
        "/api/notifications", headers=_headers(CLIENT_A)
    ).json()["notifications"]]
    assert types.count("route_changed") == 1


def test_on_route_no_deviation() -> None:
    client = make_client()
    body = _create(client, planned_geometry=[[77.0, 28.6], [77.1, 28.6]])
    resp = client.post(
        f"/api/guardian/sessions/{body['session_id']}/location",
        json={"latitude": 28.6001, "longitude": 77.05},
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 200
    assert resp.json()["deviation_detected"] is False


def test_guardian_start_records_notification() -> None:
    client = make_client()
    _create(client)
    types = [e["type"] for e in client.get(
        "/api/notifications", headers=_headers(CLIENT_A)
    ).json()["notifications"]]
    assert "guardian_started" in types
