from datetime import UTC, datetime

from app.osm_feed import map_elements_to_rows

NOW = datetime(2026, 8, 15, 10, 0, tzinfo=UTC)

STREETLAMP_OFF: dict[str, object] = {
    "type": "way",
    "id": 1001,
    "tags": {"highway": "residential", "lit": "no"},
}
NO_SIDEWALK: dict[str, object] = {
    "type": "way",
    "id": 1002,
    "tags": {"highway": "secondary", "sidewalk": "no"},
}
NO_SIDEWALK_NONE: dict[str, object] = {
    "type": "way",
    "id": 1003,
    "tags": {"highway": "residential", "sidewalk": "none"},
}
UNPAVED: dict[str, object] = {
    "type": "way",
    "id": 1004,
    "tags": {"highway": "tertiary", "surface": "gravel"},
}
UNLIT_AND_UNPAVED: dict[str, object] = {
    "type": "way",
    "id": 1005,
    "tags": {"highway": "residential", "lit": "no", "surface": "dirt"},
}
LIT_YES: dict[str, object] = {
    "type": "way",
    "id": 1006,
    "tags": {"highway": "residential", "lit": "yes"},
}
NODE_NOT_WAY: dict[str, object] = {"type": "node", "id": 1007, "tags": {"highway": "streetlamp"}}
NO_TAGS: dict[str, object] = {"type": "way", "id": 1008}
LIT_NO_ON_NON_HIGHWAY: dict[str, object] = {"type": "way", "id": 1009, "tags": {"lit": "no"}}
NOT_IN_GRAPH: dict[str, object] = {
    "type": "way",
    "id": 2001,
    "tags": {"highway": "residential", "lit": "no"},
}

SEGMENT_MAP = {
    1001: [5001],
    1002: [5002],
    1003: [5003],
    1004: [5004],
    1005: [5005, 5006],  # one way split into two graph segments
    1006: [5007],
    1009: [5009],
}


def test_maps_lit_no_to_poor_lighting_on_graph_segment() -> None:
    rows, skipped = map_elements_to_rows([STREETLAMP_OFF], NOW, SEGMENT_MAP)
    assert skipped == 0
    assert len(rows) == 1
    assert rows[0]["segment_id"] == 5001  # graph segment id, not the OSM way id
    assert rows[0]["observation_type"] == "poor_lighting"
    assert rows[0]["value_json"] == {"poor": True}


def test_maps_sidewalk_no_and_none() -> None:
    rows, _ = map_elements_to_rows([NO_SIDEWALK, NO_SIDEWALK_NONE], NOW, SEGMENT_MAP)
    assert len(rows) == 2
    assert all(r["observation_type"] == "blocked_sidewalk" for r in rows)
    assert all(r["value_json"] == {"blocked": True} for r in rows)


def test_maps_unpaved_surface_to_road_hazard() -> None:
    rows, _ = map_elements_to_rows([UNPAVED], NOW, SEGMENT_MAP)
    assert len(rows) == 1
    assert rows[0]["observation_type"] == "road_hazard"
    assert rows[0]["value_json"] == {"hazard": True, "kind": "gravel"}


def test_split_way_emits_one_row_per_graph_segment() -> None:
    rows, _ = map_elements_to_rows([UNLIT_AND_UNPAVED], NOW, SEGMENT_MAP)
    assert len(rows) == 4  # 2 segments x 2 types
    segment_ids = {r["segment_id"] for r in rows}
    assert segment_ids == {5005, 5006}
    types = {r["observation_type"] for r in rows}
    assert types == {"poor_lighting", "road_hazard"}


def test_positive_tags_and_non_matches_produce_nothing() -> None:
    rows, _ = map_elements_to_rows(
        [LIT_YES, NODE_NOT_WAY, NO_TAGS, LIT_NO_ON_NON_HIGHWAY], NOW, SEGMENT_MAP
    )
    assert rows == []


def test_way_not_in_graph_is_skipped_and_counted() -> None:
    rows, skipped = map_elements_to_rows([NOT_IN_GRAPH], NOW, SEGMENT_MAP)
    assert rows == []
    assert skipped == 1


def test_rows_are_report_level_honest() -> None:
    rows, _ = map_elements_to_rows([STREETLAMP_OFF], NOW, SEGMENT_MAP)
    assert rows[0]["verification_state"] == "REPORTED"
    assert rows[0]["source_reliability"] == 0.7
    assert rows[0]["observed_at"] == NOW.isoformat(timespec="seconds")
