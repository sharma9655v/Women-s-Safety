from __future__ import annotations

from pathlib import Path

from app.segments import map_match, nearest_road_distance_m
from app.segments.matcher import RoadSegment
from app.segments.store import MemorySegmentStore

FIXTURES = Path(__file__).parent / "fixtures"

# Route runs west->east along lat 28.60 from lon 77.20 to 77.215.
ROUTE_COORDS: list[tuple[float, float]] = [(77.2, 28.6), (77.215, 28.6)]


def test_matcher_orders_segments_along_route() -> None:
    store = MemorySegmentStore.from_geojson(FIXTURES / "segments.geojson")
    matched = map_match(ROUTE_COORDS, store.all())
    # Segments 1, 2, 3 lie on the route; 5 joins it at the middle; 4 is 0.005 deg away.
    assert matched == [1, 2, 5, 3]


def test_matcher_excludes_distant_segment() -> None:
    store = MemorySegmentStore.from_geojson(FIXTURES / "segments.geojson")
    matched = map_match(ROUTE_COORDS, store.all())
    assert 4 not in matched


def test_matcher_threshold_controls_snap_distance() -> None:
    store = MemorySegmentStore.from_geojson(FIXTURES / "segments.geojson")
    # Segment 5 is offset ~0.0012 deg from the route midpoint; a tight
    # threshold excludes it.
    matched = map_match(ROUTE_COORDS, store.all(), threshold_deg=0.0005)
    assert matched == [1, 2, 3]


def test_matcher_empty_inputs() -> None:
    assert map_match([], []) == []
    seg = RoadSegment(id=1, geometry=((77.2, 28.6), (77.205, 28.6)))
    assert map_match([], [seg]) == []
    assert map_match(ROUTE_COORDS, []) == []


def test_nearest_road_distance_on_network() -> None:
    store = MemorySegmentStore.from_geojson(FIXTURES / "segments.geojson")
    # (77.2, 28.6) is the route start, on the corridor itself.
    distance = nearest_road_distance_m(77.2, 28.6, store.all())
    assert distance is not None
    assert distance < 10.0


def test_nearest_road_distance_off_network() -> None:
    store = MemorySegmentStore.from_geojson(FIXTURES / "segments.geojson")
    # ~0.02 deg away from the corridor (~1.7 km at Delhi latitude).
    distance = nearest_road_distance_m(77.18, 28.57, store.all())
    assert distance is not None
    assert distance > 500.0


def test_nearest_road_distance_no_segments() -> None:
    assert nearest_road_distance_m(77.2, 28.6, []) is None


def test_matcher_reversed_route_order_is_detected() -> None:
    store = MemorySegmentStore.from_geojson(FIXTURES / "segments.geojson")
    matched = map_match(list(reversed(ROUTE_COORDS)), store.all())
    assert matched == [3, 5, 2, 1]


def test_matcher_rejects_short_segment_geometry() -> None:
    try:
        RoadSegment(id=9, geometry=((77.2, 28.6),))
    except ValueError:
        return
    raise AssertionError("expected ValueError for single-coordinate segment")


def test_memory_store_loads_geojson() -> None:
    store = MemorySegmentStore.from_geojson(FIXTURES / "segments.geojson")
    assert store.count() == 5
    seg = next(s for s in store.all() if s.id == 2)
    assert seg.road_type == "residential"
    assert seg.lit == "no"


class _FakeRow:
    def __init__(self, id_: int, geom: str, road_type: str | None, lit: str | None) -> None:
        self.id = id_
        self.geom = geom
        self.road_type = road_type
        self.lit = lit


class _FakeResult:
    def __init__(self, rows: list[_FakeRow]) -> None:
        self._rows = rows

    def fetchall(self) -> list[_FakeRow]:
        return self._rows


class _FakeConnection:
    def __init__(self, rows: list[_FakeRow]) -> None:
        self._rows = rows

    def execute(self, _stmt: object) -> _FakeResult:
        return _FakeResult(self._rows)

    def __enter__(self) -> _FakeConnection:
        return self

    def __exit__(self, *args: object) -> None:
        pass


class _FakeEngine:
    def __init__(self, rows: list[_FakeRow]) -> None:
        self._rows = rows

    def connect(self) -> _FakeConnection:
        return _FakeConnection(self._rows)


def test_postgis_store_parses_rows() -> None:
    from app.segments.store import PostgisSegmentStore

    rows = [
        _FakeRow(
            101,
            '{"type":"LineString","coordinates":[[77.23,28.61],[77.22,28.62]]}',
            "residential",
            "yes",
        ),
        _FakeRow(
            102,
            '{"type":"LineString","coordinates":[[77.21,28.63],[77.20,28.64]]}',
            "primary",
            None,
        ),
    ]
    store = PostgisSegmentStore(_FakeEngine(rows))  # type: ignore[arg-type]
    segments = store.all()
    assert [s.id for s in segments] == [101, 102]
    assert segments[0].geometry == ((77.23, 28.61), (77.22, 28.62))
    assert segments[0].lit == "yes"
    assert segments[1].road_type == "primary"


def test_postgis_store_skips_bad_geometry_rows() -> None:
    from app.segments.store import PostgisSegmentStore

    rows = [
        _FakeRow(1, '{"type":"LineString","coordinates":[[77.23,28.61]]}', None, None),
        _FakeRow(
            2, '{"type":"LineString","coordinates":[[77.23,28.61],[77.22,28.62]]}', None, None
        ),
    ]
    store = PostgisSegmentStore(_FakeEngine(rows))  # type: ignore[arg-type]
    assert [s.id for s in store.all()] == [2]
