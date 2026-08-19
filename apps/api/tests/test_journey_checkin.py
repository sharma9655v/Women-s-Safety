"""Journey check-in (Feature Group H): timed check-in journeys.

Regression for the frontend contract: the web client only knows the
destination name (it never geocodes), so destination_lat/lon must be
optional on create — the previous required-float schema made every
frontend start request fail with 422.
"""

from fastapi.testclient import TestClient

from app.api.guardian import _journey_checkin_limiter
from app.main import app
from app.reports.limiter import MemoryRateLimiter
from app.safety import (
    MemoryGuardianStore,
    MemoryJourneyCheckinStore,
    MemoryNotificationStore,
)
from app.safety.notifications import get_notification_store
from app.safety.sessions import get_sessions_store
from app.safety.journey_checkin import get_journey_checkin_store

CLIENT_A = "a" * 32


def make_client(*, limit: int = 10) -> TestClient:
    app.dependency_overrides = {}
    checkins = MemoryJourneyCheckinStore()
    limiter = MemoryRateLimiter(limit, 3600)
    app.dependency_overrides[get_journey_checkin_store] = lambda: checkins
    app.dependency_overrides[get_sessions_store] = lambda: MemoryGuardianStore()
    app.dependency_overrides[get_notification_store] = lambda: MemoryNotificationStore()
    app.dependency_overrides[_journey_checkin_limiter] = lambda: limiter
    return TestClient(app)


def _headers(cid: str) -> dict[str, str]:
    return {"X-Client-Id": cid}


def test_start_without_destination_coords_accepted() -> None:
    """The web client sends only a destination name — coords are optional."""
    client = make_client()
    resp = client.post(
        "/api/journey/checkins",
        json={
            "destination_name": "Khan Market",
            "destination_lat": None,
            "destination_lon": None,
            "checkin_interval_s": 900,
            "checkin_grace_s": 300,
            "contact_ids": [1],
        },
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["destination_name"] == "Khan Market"
    assert body["destination_lat"] is None
    assert body["destination_lon"] is None


def test_start_with_destination_coords_still_accepted() -> None:
    client = make_client()
    resp = client.post(
        "/api/journey/checkins",
        json={
            "destination_name": "Khan Market",
            "destination_lat": 28.6003,
            "destination_lon": 77.2273,
            "contact_ids": [1],
        },
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["destination_lat"] == 28.6003
    assert body["destination_lon"] == 77.2273


def test_out_of_range_coords_rejected() -> None:
    client = make_client()
    resp = client.post(
        "/api/journey/checkins",
        json={
            "destination_name": "Nowhere",
            "destination_lat": 123.0,
            "destination_lon": 0.0,
            "contact_ids": [1],
        },
        headers=_headers(CLIENT_A),
    )
    assert resp.status_code == 422


def test_active_returns_null_when_none() -> None:
    client = make_client()
    resp = client.get("/api/journey/checkins/active", headers=_headers(CLIENT_A))
    assert resp.status_code == 200
    assert resp.json() is None