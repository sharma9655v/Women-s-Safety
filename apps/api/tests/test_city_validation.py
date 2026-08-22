from __future__ import annotations

from app.evidence.engine import Observation
from app.evidence.states import VerificationState
from app.gis.cities import covers_coords, get_city, list_cities
from app.gis.validation import build_fixture, run_validation, validate_city


def test_city_registry_has_ten_cities() -> None:
    cities = list_cities()
    assert len(cities) == 10
    assert {c.name for c in cities} == {
        "delhi",
        "mumbai",
        "bengaluru",
        "hyderabad",
        "chennai",
        "kolkata",
        "pune",
        "noida",
        "ghaziabad",
        "jaipur",
    }
    delhi = get_city("delhi")
    assert covers_coords(delhi, 28.60, 77.20)
    assert not covers_coords(delhi, 18.90, 72.80)


def test_unknown_city_raises() -> None:
    import pytest

    from app.gis.cities import get_city

    with pytest.raises(KeyError):
        get_city("atlantis")


def test_fixture_validation_reports_synthetic_counts() -> None:
    city = get_city("mumbai")
    segments, evidence = build_fixture(city)
    report = run_validation(segments, evidence, cities=[city])
    stats = report.cities[0]
    assert stats.segments_in_city == 200
    assert stats.observations > 0
    assert stats.real_observations == 0  # fixtures are never real
    assert stats.demo_observations == 0
    assert stats.sources.get("fixture", 0) == stats.observations
    assert stats.coverage_fraction > 0.0
    assert stats.duplicate_hash_rows == 0
    assert stats.invalid_coordinate_rows == 0
    assert stats.outside_bbox_rows == 0
    assert report.total_observations == stats.observations


def test_fixture_observations_are_deterministic() -> None:
    city = get_city("delhi")
    _, evidence_a = build_fixture(city)
    _, evidence_b = build_fixture(city)
    ids_a = [obs.id for obs in evidence_a._observations]  # type: ignore[attr-defined]
    ids_b = [obs.id for obs in evidence_b._observations]  # type: ignore[attr-defined]
    assert ids_a == ids_b


def test_validate_city_empty_city_notes_missing_data() -> None:
    from app.evidence.store import MemoryEvidenceStore
    from app.segments.store import MemorySegmentStore

    city = get_city("chennai")
    segments = MemorySegmentStore([])
    evidence = MemoryEvidenceStore([])
    stats = validate_city(city, segments, evidence)
    assert stats.segments_in_city == 0
    assert stats.observations == 0
    assert any("no road segments" in note for note in stats.notes)


def test_validation_counts_demo_separately() -> None:
    from datetime import UTC, datetime

    from app.evidence.store import MemoryEvidenceStore
    from app.segments.matcher import RoadSegment
    from app.segments.store import MemorySegmentStore

    city = get_city("pune")
    seg = RoadSegment(
        id=200_001, geometry=((73.80, 18.55), (73.81, 18.56)), road_type="residential", lit="yes"
    )
    store_segments = MemorySegmentStore([seg])
    observed_at = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    store_evidence = MemoryEvidenceStore(
        [
            Observation(
                segment_id=seg.id,
                source_type="street_audit",
                observation_type="poor_lighting",
                observed_at=observed_at,
                source_reliability=0.9,
                value={"poor": True},
                state=VerificationState.REPORTED,
            ),
            Observation(
                segment_id=seg.id,
                source_type="demo_seed",
                observation_type="harassment",
                observed_at=observed_at,
                source_reliability=0.55,
                value={"incident": True},
                state=VerificationState.REPORTED,
            ),
        ]
    )
    stats = validate_city(city, store_segments, store_evidence)
    assert stats.observations == 2
    assert stats.real_observations == 1
    assert stats.demo_observations == 1
    assert stats.mean_risk is not None
