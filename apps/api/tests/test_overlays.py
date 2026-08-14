from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.overlays.store import MemoryOverlayStore, OverlayPoint
from app.overlays.registry import get_overlay_store

client = TestClient(app)


def _point(
    observation_type: str,
    lat: float = 28.63,
    lon: float = 77.22,
    observed_at: datetime | None = None,
    working: bool | None = None,
    state: str = "REPORTED",
    segment_id: int = 100,
) -> OverlayPoint:
    return OverlayPoint(
        observation_id=1,
        segment_id=segment_id,
        observation_type=observation_type,
        source_type="demo_seed",
        observed_at=observed_at or datetime.now(UTC),
        verification_state=state,
        working=working,
        lat=lat,
        lon=lon,
        area_name="Connaught Place",
    )


def _override_store(points: list[OverlayPoint]) -> None:
    store = MemoryOverlayStore(points)
    app.dependency_overrides[get_overlay_store] = lambda: store


def test_incidents_endpoint_filters_observation_types():
    _override_store(
        [
            _point("harassment"),
            _point("suspicious_activity"),
            _point("streetlight_not_working", working=False),
            _point("poor_lighting"),
        ]
    )
    resp = client.get("/api/incidents")
    assert resp.status_code == 200
    incidents = resp.json()
    assert len(incidents) == 2
    assert {i["category"] for i in incidents} == {"harassment", "suspicious_activity"}
    assert all(i["location"]["lat"] == 28.63 for i in incidents)
    assert all(i["source"] == "demo_seed" for i in incidents)


def test_lighting_endpoint_exposes_working_state():
    _override_store(
        [
            _point("streetlight_not_working", working=False, segment_id=1),
            _point("streetlight_not_working", working=True, segment_id=2),
            _point("poor_lighting", segment_id=3),
        ]
    )
    resp = client.get("/api/lighting")
    assert resp.status_code == 200
    lighting = resp.json()
    assert len(lighting) == 3
    by_status = {l["status_label"] for l in lighting}
    assert "Streetlight reported not working" in by_status
    assert "Lighting evidence available" in by_status
    assert all(l["lat"] == 28.63 for l in lighting)


def test_bbox_filters_points():
    _override_store(
        [
            _point("harassment", lat=28.63, lon=77.22),
            _point("harassment", lat=28.90, lon=77.40),
        ]
    )
    resp = client.get(
        "/api/incidents", params={"min_lon": 77.0, "min_lat": 28.3, "max_lon": 77.3, "max_lat": 28.7}
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_alerts_return_recent_incidents_sorted():
    old = _point("harassment", observed_at=datetime.now(UTC) - timedelta(days=10), segment_id=1)
    recent = _point("harassment", observed_at=datetime.now(UTC), segment_id=2)
    _override_store([old, recent])
    resp = client.get("/api/alerts")
    assert resp.status_code == 200
    alerts = resp.json()
    assert len(alerts) == 2
    assert alerts[0]["reported_at"] >= alerts[1]["reported_at"]


def test_area_safety_unknown_area_returns_graceful_shape():
    _override_store([])
    resp = client.get("/api/safety/area", params={"name": "nowhere-ville"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["recent_incidents"] == 0
    assert body["by_time_of_day"] == []


def test_heatmap_returns_zones_within_bbox():
    _override_store([_point("harassment", lat=28.63, lon=77.22)])
    resp = client.get("/api/safety/heatmap")
    assert resp.status_code == 200
    zones = resp.json()
    assert len(zones) >= 1
    assert 0 <= zones[0]["level"] <= 1


def test_route_request_accepts_hour_ist_override():
    _override_store([])
    resp = client.post(
        "/api/routes",
        json={
            "origin": {"lat": 28.6315, "lon": 77.2167},
            "destination": {"lat": 28.6129, "lon": 77.2295},
            "mode": "walking",
            "hour_ist": 22,
        },
    )
    assert resp.status_code in (200, 502, 503)
