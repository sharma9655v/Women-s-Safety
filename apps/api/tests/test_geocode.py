from __future__ import annotations

from fastapi.testclient import TestClient

from app.facilities import get_facilities_store
from app.facilities.store import Facility, MemoryFacilityStore
from app.main import app


def make_client() -> TestClient:
    app.dependency_overrides = {}
    app.dependency_overrides[get_facilities_store] = lambda: MemoryFacilityStore(
        [
            Facility(id=1, type="police", name="Connaught Police", lon=77.23, lat=28.61),
            Facility(id=2, type="hospital", name="All India Institute", lon=77.2, lat=28.6),
        ]
    )
    return TestClient(app)


def test_geocode_facility_match() -> None:
    resp = make_client().get("/api/geocode", params={"q": "connaught"})
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert any(
        r["name"] == "Connaught Police" and r["kind"] == "facility" and r["type"] == "police"
        for r in results
    )


def test_geocode_area_match_from_arEA_CENTERS() -> None:
    resp = make_client().get("/api/geocode", params={"q": "connaught place"})
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert any(r["kind"] == "area" and r["name"] == "Connaught Place" for r in results)


def test_geocode_empty_query_returns_nothing() -> None:
    resp = make_client().get("/api/geocode", params={"q": "   "})
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_geocode_no_match_returns_empty() -> None:
    resp = make_client().get("/api/geocode", params={"q": "zzzznotathing"})
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_geocode_respects_limit() -> None:
    resp = make_client().get("/api/geocode", params={"q": "i", "limit": 1})
    results = resp.json()["results"]
    assert len(results) <= 1
