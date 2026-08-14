import httpx
from fastapi.testclient import TestClient
from httpx import MockTransport, Response

from app.main import app
from app.routing.osrm import build_route_url
from app.schemas import LatLon

DELHI_A = LatLon(lat=28.61, lon=77.23)
DELHI_B = LatLon(lat=28.63, lon=77.21)


def osrm_success_handler(request) -> Response:
    assert "alternatives=2" in str(request.url)
    assert "geometries=geojson" in str(request.url)
    return Response(
        200,
        json={
            "code": "Ok",
            "routes": [
                {
                    "distance": 3241.5,
                    "duration": 2374.2,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[77.23, 28.61], [77.22, 28.62], [77.21, 28.63]],
                    },
                },
                {
                    "distance": 4120.1,
                    "duration": 3011.0,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[77.23, 28.61], [77.21, 28.62], [77.21, 28.63]],
                    },
                },
                {
                    "distance": 5010.7,
                    "duration": 3555.9,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[77.23, 28.61], [77.20, 28.62], [77.21, 28.63]],
                    },
                },
            ],
        },
    )


def osrm_error_handler(request) -> Response:
    return Response(
        400,
        json={
            "code": "NoRoute",
            "message": "Impossible route between points",
        },
    )


def osrm_unreachable_handler(request) -> Response:
    raise httpx.ConnectTimeout("connection timed out", request=request)


def make_client(handler) -> TestClient:
    app.dependency_overrides = {}
    transport = MockTransport(handler)
    from app.api.routes import get_osrm
    from app.evidence import MemoryEvidenceStore, get_evidence_store
    from app.facilities import Facility, MemoryFacilityStore
    from app.facilities.registry import get_facilities_store
    from app.segments import get_segments_store
    from app.segments.matcher import RoadSegment
    from app.segments.store import MemorySegmentStore

    def override_osrm() -> object:
        from app.routing import OsrmClient

        return OsrmClient("http://osrm.test", transport=transport)

    def override_segments() -> object:
        # Two segments that lie on the primary route's first leg.
        return MemorySegmentStore(
            [
                RoadSegment(id=11, geometry=((77.23, 28.61), (77.225, 28.615))),
                RoadSegment(id=12, geometry=((77.225, 28.615), (77.22, 28.62))),
                RoadSegment(id=99, geometry=((77.10, 28.50), (77.11, 28.51))),
            ]
        )

    def override_evidence() -> object:
        return MemoryEvidenceStore(segment_ids=[11, 12])

    def override_facilities() -> object:
        return MemoryFacilityStore(
            [
                Facility(id=1, type="police", name="Test Police", lon=77.22, lat=28.615),
                Facility(id=2, type="cafe", name="Cafe", lon=77.30, lat=28.70),
            ]
        )

    app.dependency_overrides[get_osrm] = override_osrm
    app.dependency_overrides[get_segments_store] = override_segments
    app.dependency_overrides[get_evidence_store] = override_evidence
    app.dependency_overrides[get_facilities_store] = override_facilities
    return TestClient(app)


def test_build_route_url_walking() -> None:
    url = build_route_url("http://osrm:5000", DELHI_A, DELHI_B, "walking")
    assert url.startswith("http://osrm:5000/route/v1/foot/77.23,28.61;77.21,28.63?")
    assert "alternatives=2" in url


def test_build_route_url_profile_map() -> None:
    assert "/foot/" in build_route_url("http://x", DELHI_A, DELHI_B, "walking")
    assert "/car/" in build_route_url("http://x", DELHI_A, DELHI_B, "driving")
    assert "/bicycle/" in build_route_url("http://x", DELHI_A, DELHI_B, "cycling")


def test_routes_returns_three_ranked_route_types() -> None:
    client = make_client(osrm_success_handler)
    resp = client.post(
        "/api/routes",
        json={
            "origin": {"lat": DELHI_A.lat, "lon": DELHI_A.lon},
            "destination": {"lat": DELHI_B.lat, "lon": DELHI_B.lon},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [route["route_type"] for route in body["routes"]] == [
        "safety_priority",
        "balanced",
        "time_priority",
    ]
    first = body["routes"][0]
    assert first["distance_m"] > 0
    assert 0.0 <= first["risk_probability"] <= 1.0
    assert 0 <= first["estimated_safety"] <= 100
    assert 0.0 <= first["confidence"] <= 1.0
    assert first["model_version"] == "deterministic-baseline-v1"
    assert first["geometry"]["type"] == "LineString"
    assert first["geometry"]["coordinates"][0] == [77.23, 28.61]


def test_routes_candidates_carry_matched_segment_ids() -> None:
    client = make_client(osrm_success_handler)
    resp = client.post(
        "/api/routes",
        json={
            "origin": {"lat": DELHI_A.lat, "lon": DELHI_A.lon},
            "destination": {"lat": DELHI_B.lat, "lon": DELHI_B.lon},
        },
    )
    body = resp.json()
    # Route 0's first leg passes through segments 11 then 12; segment 99 is far away.
    assert [11, 12] in [route["segment_ids"] for route in body["routes"]]


def test_routes_never_claim_safety_and_include_reasons() -> None:
    client = make_client(osrm_success_handler)
    resp = client.post(
        "/api/routes",
        json={
            "origin": {"lat": DELHI_A.lat, "lon": DELHI_A.lon},
            "destination": {"lat": DELHI_B.lat, "lon": DELHI_B.lon},
        },
    )
    body = resp.json()
    flat = str(body).lower()
    assert '"safe": true' not in flat
    assert "safe" not in body["routes"][0]
    assert isinstance(body["routes"][0]["reasons"], list)
    assert isinstance(body["routes"][0]["warnings"], list)


def test_routes_round_trip_is_deterministic() -> None:
    client = make_client(osrm_success_handler)
    payload = {
        "origin": {"lat": DELHI_A.lat, "lon": DELHI_A.lon},
        "destination": {"lat": DELHI_B.lat, "lon": DELHI_B.lon},
    }
    first = client.post("/api/routes", json=payload).json()
    second = client.post("/api/routes", json=payload).json()
    for a, b in zip(first["routes"], second["routes"], strict=True):
        assert a["route_type"] == b["route_type"]
        assert a["segment_ids"] == b["segment_ids"]
        assert a["reasons"] == b["reasons"]
        assert round(a["risk_probability"], 4) == round(b["risk_probability"], 4)


def test_routes_validation_rejects_bad_coordinates() -> None:
    client = make_client(osrm_success_handler)
    resp = client.post(
        "/api/routes",
        json={
            "origin": {"lat": 91.0, "lon": 0.0},
            "destination": {"lat": 0.0, "lon": 181.0},
            "mode": "walking",
        },
    )
    assert resp.status_code == 422


def test_routes_rejects_unknown_mode() -> None:
    client = make_client(osrm_success_handler)
    resp = client.post(
        "/api/routes",
        json={
            "origin": {"lat": 28.61, "lon": 77.23},
            "destination": {"lat": 28.63, "lon": 77.21},
            "mode": "teleport",
        },
    )
    assert resp.status_code == 422


def test_routes_osrm_error_is_explicit_502() -> None:
    client = make_client(osrm_error_handler)
    resp = client.post(
        "/api/routes",
        json={
            "origin": {"lat": DELHI_A.lat, "lon": DELHI_A.lon},
            "destination": {"lat": DELHI_B.lat, "lon": DELHI_B.lon},
        },
    )
    assert resp.status_code == 502
    assert "NoRoute" in resp.json()["detail"]


def test_routes_osrm_unreachable_is_503() -> None:
    client = make_client(osrm_unreachable_handler)
    resp = client.post(
        "/api/routes",
        json={
            "origin": {"lat": DELHI_A.lat, "lon": DELHI_A.lon},
            "destination": {"lat": DELHI_B.lat, "lon": DELHI_B.lon},
        },
    )
    assert resp.status_code == 503
    assert "unreachable" in resp.json()["detail"]


def test_routes_empty_result_is_explicit_error() -> None:
    client = make_client(lambda request: Response(200, json={"code": "Ok", "routes": []}))
    resp = client.post(
        "/api/routes",
        json={
            "origin": {"lat": DELHI_A.lat, "lon": DELHI_A.lon},
            "destination": {"lat": DELHI_B.lat, "lon": DELHI_B.lon},
        },
    )
    assert resp.status_code == 502
    assert "no route" in resp.json()["detail"]
