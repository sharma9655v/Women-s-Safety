from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.evidence import Observation, aggregate
from app.risk import (
    MODEL_VERSION,
    assign_route_types,
    compute_segment_risk,
    haversine_m,
    profile_cost,
    route_warnings,
    score_candidate,
    segment_length_m,
)
from app.risk.model import SegmentRisk

NOW = datetime(2026, 8, 10, 12, 0, 0, tzinfo=UTC)


def obs(
    segment_id: int,
    obs_type: str,
    observed_at: datetime,
    source: str = "user_report",
    reliability: float = 0.6,
    value: dict[str, object] | None = None,
) -> Observation:
    return Observation(
        segment_id=segment_id,
        source_type=source,
        observation_type=obs_type,
        observed_at=observed_at,
        source_reliability=reliability,
        value=value or {},
    )


def risk(
    segment_id: int = 1,
    evidence=None,
    road_type: str | None = None,
    lit: str | None = None,
    nearest_emergency_m: float | None = None,
    hour_ist: int = 14,
) -> SegmentRisk:
    return compute_segment_risk(
        segment_id=segment_id,
        evidence=evidence,
        road_type=road_type,
        lit=lit,
        nearest_emergency_m=nearest_emergency_m,
        hour_ist=hour_ist,
    )


# --- risk model -------------------------------------------------------------


def test_risk_bounded_and_sparse_without_evidence() -> None:
    r = risk()
    assert 0.0 <= r.risk_probability <= 1.0
    assert r.confidence == 0.25
    assert r.uncertainty == 0.75
    assert "Limited safety data for this segment" in r.reasons


def test_risk_confidence_rises_with_evidence_and_drops_on_conflict() -> None:
    items = [
        obs(1, "harassment", NOW - timedelta(hours=3)),
        obs(1, "harassment", NOW - timedelta(hours=5), source="city_data", reliability=0.9),
    ]
    evidence = aggregate(1, items, NOW)
    r = risk(evidence=evidence)
    assert r.confidence > 0.25
    assert r.confidence <= 0.95

    conflicting = aggregate(
        1,
        [
            obs(1, "blocked_sidewalk", NOW, value={"blocked": True}),
            obs(1, "blocked_sidewalk", NOW - timedelta(hours=1), value={"blocked": False}),
        ],
        NOW,
    )
    rc = risk(evidence=conflicting)
    assert rc.confidence < r.confidence
    assert "Conflicting recent evidence on this segment" in rc.reasons


def test_risk_incident_evidence_raises_risk() -> None:
    base = risk()
    evidence = aggregate(
        1,
        [
            obs(1, "harassment", NOW - timedelta(hours=1)),
            obs(1, "suspicious_activity", NOW - timedelta(hours=4)),
        ],
        NOW,
    )
    with_incidents = risk(evidence=evidence)
    assert with_incidents.risk_probability > base.risk_probability
    assert "Recent incident reports on this segment" in with_incidents.reasons


def test_risk_lighting_evidence_raises_risk() -> None:
    evidence = aggregate(
        1,
        [obs(1, "streetlight_not_working", NOW - timedelta(days=2), value={"working": False})],
        NOW,
    )
    r = risk(evidence=evidence)
    assert "Streetlight failure reported on this segment" in r.reasons
    assert r.risk_probability > risk().risk_probability


def test_risk_night_is_riskier_than_day() -> None:
    r_day = risk(hour_ist=14)
    r_night = risk(hour_ist=23)
    assert r_night.risk_probability >= r_day.risk_probability


def test_risk_lit_tag_reduces_night_lighting_risk() -> None:
    evidence = aggregate(
        1,
        [obs(1, "streetlight_not_working", NOW - timedelta(hours=12), value={"working": False})],
        NOW,
    )
    unlit = risk(evidence=evidence, lit="no", hour_ist=23)
    lit = risk(evidence=evidence, lit="yes", hour_ist=23)
    assert lit.risk_probability < unlit.risk_probability


def test_risk_facility_proximity_lowers_risk() -> None:
    near = risk(nearest_emergency_m=300.0)
    far = risk(nearest_emergency_m=2900.0)
    assert near.risk_probability < far.risk_probability
    assert "Near an emergency facility" in near.reasons
    assert "No emergency facility within 3 km" in risk(nearest_emergency_m=None).reasons


def test_risk_footway_at_night_raises_risk() -> None:
    night = risk(road_type="footway", hour_ist=23).risk_probability
    day = risk(road_type="footway", hour_ist=14).risk_probability
    assert night > day


def test_risk_is_deterministic() -> None:
    evidence = aggregate(1, [], NOW)
    assert risk(evidence=evidence, road_type="footway", hour_ist=23) == risk(
        evidence=evidence, road_type="footway", hour_ist=23
    )


# --- routing -----------------------------------------------------------------


def _segment_risk(segment_id: int, risk_value: float, confidence: float = 0.5) -> SegmentRisk:
    return SegmentRisk(
        segment_id=segment_id,
        risk_probability=risk_value,
        confidence=confidence,
        uncertainty=1.0 - confidence,
        reasons=(),
    )


def test_haversine_m_sanity() -> None:
    # ~111 km per degree of latitude.
    assert haversine_m(0.0, 0.0, 0.0, 1.0) == pytest.approx(111_195)
    assert haversine_m(77.21, 28.61, 77.21, 28.61) == 0.0


def test_segment_length_m_sums_edges() -> None:
    length = segment_length_m(((0.0, 0.0), (0.0, 1.0), (0.0, 2.0)))
    assert length == pytest.approx(2 * 111_195, rel=1e-3)


def test_score_candidate_length_weighted_risk() -> None:
    scored = score_candidate(
        candidate_index=0,
        distance_m=1000.0,
        duration_s=800.0,
        segment_lengths=[1.0, 3.0],
        segment_risks=[_segment_risk(1, 1.0), _segment_risk(2, 0.0)],
    )
    assert scored.risk_probability == pytest.approx(0.25)
    assert scored.segment_lengths == (1.0, 3.0)
    assert scored.confidence == pytest.approx(0.5)


def test_assign_route_types_picks_per_profile() -> None:
    short_risky = score_candidate(0, 2000.0, 1500.0, [100.0], [_segment_risk(1, 0.4)])
    long_safe = score_candidate(1, 2300.0, 1650.0, [100.0], [_segment_risk(2, 0.05)])
    chosen = assign_route_types([short_risky, long_safe])
    assert chosen["safety_priority"] is long_safe
    assert chosen["time_priority"] is short_risky
    assert chosen["balanced"] is long_safe


def test_profile_cost_risk_weights_scale_with_preference() -> None:
    low = score_candidate(0, 3000.0, 2200.0, [100.0], [_segment_risk(1, 0.1)])
    high = score_candidate(1, 3000.0, 2200.0, [100.0], [_segment_risk(2, 0.9)])
    # Same distance/time: the safety profile penalizes added risk far more
    # than the time profile does.
    delta_safety = profile_cost(high, "safety_priority") - profile_cost(low, "safety_priority")
    delta_time = profile_cost(high, "time_priority") - profile_cost(low, "time_priority")
    assert delta_safety > delta_time


def test_route_warnings_sparse_and_conflict() -> None:
    sparse = score_candidate(0, 100.0, 80.0, [1.0], [_segment_risk(1, 0.2, confidence=0.25)])
    assert route_warnings(sparse) == ["Limited safety data along parts of this route"]

    conflict_risk = SegmentRisk(
        segment_id=1,
        risk_probability=0.2,
        confidence=0.5,
        uncertainty=0.5,
        reasons=("Conflicting recent evidence on this segment",),
    )
    conflicting = score_candidate(0, 100.0, 80.0, [1.0], [conflict_risk])
    assert "Conflicting recent evidence on parts of this route" in route_warnings(conflicting)


def test_model_version_is_baseline() -> None:
    assert MODEL_VERSION == "deterministic-baseline-v1"


def test_high_risk_fraction_and_risk_exposure() -> None:
    risks = [_segment_risk(1, 0.1), _segment_risk(2, 0.9), _segment_risk(3, 0.6)]
    lengths = [100.0, 100.0, 200.0]
    scored = score_candidate(0, 400.0, 300.0, lengths, risks)
    # High-risk stretches (>= 0.5): segments 2 and 3 = 300 of 400 m.
    assert scored.high_risk_fraction == pytest.approx(0.75)
    # Exposure = sum(length x risk) = 10 + 90 + 120.
    assert scored.risk_exposure_m == pytest.approx(220.0)


def test_high_risk_fraction_zero_below_threshold() -> None:
    scored = score_candidate(0, 100.0, 80.0, [100.0], [_segment_risk(1, 0.4)])
    assert scored.high_risk_fraction == 0.0
    assert scored.risk_exposure_m == pytest.approx(40.0)


def test_risk_exposure_zero_without_lengths() -> None:
    # Unknown segment lengths -> exposure is 0, honestly, not invented.
    scored = score_candidate(0, 100.0, 80.0, [], [_segment_risk(1, 0.9)])
    assert scored.risk_exposure_m == 0.0
    assert 0.0 <= scored.high_risk_fraction <= 1.0
