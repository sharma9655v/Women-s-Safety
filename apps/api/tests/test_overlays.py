from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.overlays.registry import get_overlay_store
from app.overlays.store import MemoryOverlayStore, OverlayPoint

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
    by_status = {item["status_label"] for item in lighting}
    assert "Streetlight reported not working" in by_status
    assert "Lighting evidence available" in by_status
    assert all(item["lat"] == 28.63 for item in lighting)


def test_bbox_filters_points():
    _override_store(
        [
            _point("harassment", lat=28.63, lon=77.22),
            _point("harassment", lat=28.90, lon=77.40),
        ]
    )
    resp = client.get(
        "/api/incidents",
        params={"min_lon": 77.0, "min_lat": 28.3, "max_lon": 77.3, "max_lat": 28.7},
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


def test_areas_endpoint_returns_known_area_summaries():
    _override_store(
        [
            _point("harassment", lat=28.6315, lon=77.2167, segment_id=1),
            _point("harassment", lat=28.6129, lon=77.2295, segment_id=2),
        ]
    )
    resp = client.get("/api/safety/areas")
    assert resp.status_code == 200
    areas = resp.json()
    assert isinstance(areas, list)
    assert len(areas) >= 1
    names = {a["area_name"] for a in areas}
    assert "Connaught Place" in names
    assert all("score" in a and "recent_incidents" in a for a in areas)


def test_facilities_endpoint_returns_bbox_rows_with_expected_shape():
    from app.facilities import Facility, get_facilities_store
    from app.facilities.store import MemoryFacilityStore

    app.dependency_overrides[get_facilities_store] = lambda: MemoryFacilityStore(
        [
            Facility(id=1, type="police", name="Police HQ", lon=77.21, lat=28.63),
            Facility(id=2, type="hospital", name="City Hospital", lon=77.22, lat=28.64),
        ]
    )
    try:
        resp = client.get("/api/facilities")
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) == 2
        first = rows[0]
        assert set(first) == {"id", "type", "name", "lat", "lon", "distance_m"}
        assert first["type"] == "police"
        assert first["distance_m"] is None
        assert first["lat"] == 28.63
    finally:
        app.dependency_overrides.pop(get_facilities_store, None)


def test_facilities_endpoint_is_empty_without_data():
    from app.facilities import get_facilities_store
    from app.facilities.store import MemoryFacilityStore

    app.dependency_overrides[get_facilities_store] = lambda: MemoryFacilityStore()
    try:
        resp = client.get("/api/facilities")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.pop(get_facilities_store, None)


def test_incidents_include_road_hazard_category():
    _override_store([_point("road_hazard", lat=28.63, lon=77.22, segment_id=1)])
    resp = client.get("/api/incidents")
    assert resp.status_code == 200
    incidents = resp.json()
    assert len(incidents) == 1
    assert incidents[0]["category"] == "road_hazard"


def test_route_request_accepts_hour_ist_override():
    import httpx
    from app.api.routes import get_osrm
    from app.evidence import MemoryEvidenceStore, get_evidence_store
    from app.facilities import MemoryFacilityStore
    from app.facilities.registry import get_facilities_store
    from app.routing import OsrmClient
    from app.segments import get_segments_store
    from app.segments.store import MemorySegmentStore

    _override_store([])
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            503, json={"code": "Unavailable", "message": "OSRM mock unavailable"}
        )
    )
    app.dependency_overrides[get_osrm] = lambda: OsrmClient("http://osrm.test", transport=transport)
    app.dependency_overrides[get_segments_store] = lambda: MemorySegmentStore.empty()
    app.dependency_overrides[get_evidence_store] = lambda: MemoryEvidenceStore()
    app.dependency_overrides[get_facilities_store] = lambda: MemoryFacilityStore([])
    try:
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
    finally:
        app.dependency_overrides.pop(get_osrm, None)
        app.dependency_overrides.pop(get_segments_store, None)
        app.dependency_overrides.pop(get_evidence_store, None)
        app.dependency_overrides.pop(get_facilities_store, None)


