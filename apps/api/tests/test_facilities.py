import pytest
from httpx import MockTransport, Response

from app.facilities import FacilityFetcher, classify, validate_bbox
from app.facilities.store import Facility, MemoryFacilityStore

DELHI_BBOX = (76.9, 28.4, 77.4, 28.9)


def overpass_payload():
    police = {
        "type": "node",
        "id": 1001,
        "lat": 28.61,
        "lon": 77.23,
        "tags": {"amenity": "police", "name": "Connaught Police"},
    }
    bus = {
        "type": "node",
        "id": 1002,
        "lat": 28.62,
        "lon": 77.22,
        "tags": {"highway": "bus_stop", "name": "Rajiv Chowk"},
    }
    hospital = {
        "type": "node",
        "id": 1003,
        "lat": 28.63,
        "lon": 77.21,
        "tags": {"amenity": "hospital"},
    }
    park = {
        "type": "node",
        "id": 1004,
        "lat": 28.64,
        "lon": 77.20,
        "tags": {"leisure": "park"},
    }
    way = {"type": "way", "id": 2001, "tags": {"amenity": "police"}}
    bakery = {
        "type": "node",
        "id": 1005,
        "lat": 28.65,
        "lon": 77.19,
        "tags": {"shop": "bakery"},
    }
    return {"version": 0.6, "elements": [police, bus, hospital, park, way, bakery]}


def test_build_query_covers_all_facility_types() -> None:
    from app.facilities.fetcher import build_query

    query = build_query(*DELHI_BBOX)
    assert '["amenity"="police"]' in query
    assert '["amenity"="hospital"]' in query
    assert '["highway"="bus_stop"]' in query
    assert '["railway"~"^(station|tram_stop)$"]' in query
    assert "28.4,76.9,28.9,77.4" in query


def test_fetch_returns_typed_features() -> None:
    calls = []

    def handler(request) -> Response:
        calls.append(request)
        return Response(200, json=overpass_payload())

    fetcher = FacilityFetcher(base_url="https://overpass.test", transport=MockTransport(handler))
    collection = fetcher.fetch(*DELHI_BBOX)

    assert len(calls) == 1
    assert calls[0].method == "POST"
    assert b"amenity" in calls[0].content

    features = collection["features"]
    assert len(features) == 4
    by_id = {f["id"]: f for f in features}
    assert by_id[1001]["properties"]["type"] == "police"
    assert by_id[1001]["properties"]["name"] == "Connaught Police"
    assert by_id[1002]["properties"]["type"] == "transit_stop"
    assert by_id[1003]["properties"]["type"] == "hospital"
    assert by_id[1003]["properties"]["name"] is None
    assert by_id[1004]["properties"]["type"] == "public_place"
    assert by_id[1001]["geometry"]["coordinates"] == [77.23, 28.61]


def test_fetch_skips_ways_and_unclassified_nodes() -> None:
    def handler(request) -> Response:
        return Response(200, json=overpass_payload())

    fetcher = FacilityFetcher(base_url="https://overpass.test", transport=MockTransport(handler))
    collection = fetcher.fetch(*DELHI_BBOX)
    ids = {f["id"] for f in collection["features"]}
    assert 2001 not in ids
    assert 1005 not in ids


def test_classify_mapping() -> None:
    assert classify({"amenity": "police"}) == "police"
    assert classify({"railway": "tram_stop"}) == "transit_stop"
    assert classify({"shop": "bakery"}) is None
    assert classify({}) is None


def test_validate_bbox() -> None:
    validate_bbox(*DELHI_BBOX)
    with pytest.raises(ValueError):
        validate_bbox(0.0, 91.0, 1.0, 92.0)
    with pytest.raises(ValueError):
        validate_bbox(77.4, 28.4, 76.9, 28.9)


def test_facility_search_matches_name_case_insensitively() -> None:
    store = MemoryFacilityStore(
        [
            Facility(id=1, type="police", name="Connaught Police", lon=77.23, lat=28.61),
            Facility(id=2, type="hospital", name="All India Institute", lon=77.2, lat=28.6),
            Facility(id=3, type="police", name="Karol Bagh Police", lon=77.19, lat=28.65),
        ]
    )
    hits = store.search("connaught")
    assert [f.id for f in hits] == [1]
    hits = store.search("POLICE")
    assert {f.id for f in hits} == {1, 3}


def test_facility_search_empty_and_limit() -> None:
    store = MemoryFacilityStore(
        [Facility(id=1, type="police", name="Police A", lon=77.23, lat=28.61)]
    )
    assert store.search("") == []
    assert store.search("   ") == []
    assert store.search("police", limit=0) == []
    assert store.search("nope") == []
