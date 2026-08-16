from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.evidence import get_evidence_store
from app.evidence import (
    Observation,
    VerificationState,
    aggregate,
    compute_states,
    evidence_hash,
    expires_at,
    freshness,
    is_expired,
    lambda_for,
)
from app.evidence.store import MemoryEvidenceStore
from app.main import app

NOW = datetime(2026, 8, 10, 12, 0, 0, tzinfo=UTC)


def obs(
    segment_id: int,
    obs_type: str,
    observed_at: datetime,
    source: str = "user_report",
    reliability: float = 0.6,
    value: dict[str, object] | None = None,
    state: VerificationState = VerificationState.REPORTED,
    **kwargs: object,
) -> Observation:
    return Observation(
        segment_id=segment_id,
        source_type=source,
        observation_type=obs_type,
        observed_at=observed_at,
        source_reliability=reliability,
        value=value or {},
        state=state,
        **kwargs,
    )


# --- freshness/decay --------------------------------------------------------


def test_freshness_is_one_at_observation_time() -> None:
    assert freshness(NOW, NOW, "harassment") == 1.0


def test_freshness_decays_exponentially() -> None:
    age = NOW - timedelta(days=1)
    f = freshness(age, NOW, "harassment")
    assert f == pytest.approx(math.exp(-lambda_for("harassment")))
    assert 0.0 < f < 1.0


def test_per_type_rates_differ() -> None:
    age = NOW - timedelta(days=7)
    slow = freshness(age, NOW, "streetlight_not_working")
    fast = freshness(age, NOW, "harassment")
    assert slow > fast


def test_freshness_clamped_to_zero_and_one() -> None:
    future = NOW + timedelta(days=10)
    assert freshness(future, NOW, "other") == 1.0
    very_old = NOW - timedelta(days=5000)
    assert freshness(very_old, NOW, "other") == 0.0


def test_expiry_after_type_specific_window() -> None:
    past = NOW - timedelta(days=200)
    assert is_expired(past, NOW, "streetlight_not_working")
    assert is_expired(past, NOW, "other")
    moderate = NOW - timedelta(days=60)
    assert not is_expired(moderate, NOW, "streetlight_not_working")
    assert is_expired(moderate, NOW, "other")
    assert expires_at(NOW, "other") < expires_at(NOW, "streetlight_not_working")


# --- state machine ----------------------------------------------------------


def test_single_report_stays_reported() -> None:
    items = compute_states([obs(1, "harassment", NOW)], NOW)
    assert items[0].state is VerificationState.REPORTED


def test_two_independent_sources_corroborate() -> None:
    items = compute_states(
        [
            obs(1, "streetlight_not_working", NOW, source="user_report"),
            obs(
                1,
                "streetlight_not_working",
                NOW - timedelta(hours=2),
                source="city_data",
                reliability=0.9,
            ),
        ],
        NOW,
    )
    assert {i.state for i in items} == {VerificationState.CORROBORATED}


def test_three_same_source_items_corroborate() -> None:
    items = compute_states(
        [
            obs(1, "harassment", NOW - timedelta(days=1)),
            obs(1, "harassment", NOW - timedelta(days=2)),
            obs(1, "harassment", NOW - timedelta(days=3)),
        ],
        NOW,
    )
    assert {i.state for i in items} == {VerificationState.CORROBORATED}


def test_conflicting_observations_detected() -> None:
    items = compute_states(
        [
            obs(1, "streetlight_not_working", NOW, value={"working": False}),
            obs(1, "streetlight_not_working", NOW - timedelta(hours=3), value={"working": True}),
        ],
        NOW,
    )
    assert {i.state for i in items} == {VerificationState.CONFLICTING}


def test_expired_observation_marks_expired() -> None:
    old = obs(1, "harassment", NOW - timedelta(days=60))
    items = compute_states([old], NOW)
    assert items[0].state is VerificationState.EXPIRED


def test_verified_and_rejected_never_transition() -> None:
    verified = obs(1, "poor_lighting", NOW, state=VerificationState.VERIFIED)
    rejected = obs(1, "poor_lighting", NOW - timedelta(days=60), state=VerificationState.REJECTED)
    items = compute_states([verified, rejected], NOW)
    assert items[0].state is VerificationState.VERIFIED
    assert items[1].state is VerificationState.REJECTED


def test_state_transitions_do_not_mutate_inputs() -> None:
    original = obs(1, "harassment", NOW - timedelta(days=60))
    compute_states([original], NOW)
    assert original.state is VerificationState.REPORTED


# --- aggregation ------------------------------------------------------------


def test_aggregate_excludes_expired_and_rejected() -> None:
    items = [
        obs(1, "harassment", NOW - timedelta(hours=1)),
        obs(1, "harassment", NOW - timedelta(days=60)),  # expired
        obs(1, "harassment", NOW - timedelta(hours=2), state=VerificationState.REJECTED),
    ]
    evidence = aggregate(1, items, NOW)
    assert evidence.total_observations == 1
    summary = evidence.by_type["harassment"]
    assert summary.count == 1
    assert summary.state_counts == {"REPORTED": 1, "EXPIRED": 1, "REJECTED": 1}


def test_aggregate_scores_by_reliability_and_recency() -> None:
    reliable = obs(1, "road_hazard", NOW - timedelta(hours=1), source="city_data", reliability=0.9)
    weak = obs(1, "road_hazard", NOW - timedelta(days=5), reliability=0.6)
    evidence = aggregate(1, [reliable, weak], NOW)
    summary = evidence.by_type["road_hazard"]
    assert summary.score == pytest.approx(
        freshness(reliable.observed_at, NOW, "road_hazard") * 0.9
        + freshness(weak.observed_at, NOW, "road_hazard") * 0.6
    )
    assert summary.source_counts == {"city_data": 1, "user_report": 1}
    assert 0.0 < summary.confidence <= 0.95


def test_aggregate_no_evidence_is_empty() -> None:
    evidence = aggregate(1, [], NOW)
    assert evidence.total_observations == 0
    assert evidence.overall_confidence == 0.0
    assert evidence.overall_freshness == 0.0
    assert evidence.by_type == {}
    assert evidence.conflicts == []


def test_aggregate_marks_conflicting_types() -> None:
    items = [
        obs(1, "blocked_sidewalk", NOW, value={"blocked": True}),
        obs(1, "blocked_sidewalk", NOW - timedelta(hours=1), value={"blocked": False}),
    ]
    evidence = aggregate(1, items, NOW)
    assert evidence.conflicts == ["blocked_sidewalk"]
    summary = evidence.by_type["blocked_sidewalk"]
    assert summary.conflicts is True
    # conflict penalty halves confidence vs the uncapped value
    assert summary.confidence < 0.5


def test_aggregate_incidents_never_conflict() -> None:
    items = [
        obs(1, "harassment", NOW - timedelta(hours=1), value={"severity": 2}),
        obs(1, "harassment", NOW - timedelta(hours=2), value={"severity": 5}),
    ]
    evidence = aggregate(1, items, NOW)
    assert evidence.conflicts == []


def test_aggregate_surfaces_source_diversity() -> None:
    items = [
        obs(1, "harassment", NOW, source="user_report"),
        obs(1, "harassment", NOW, source="city_data"),
    ]
    summary = aggregate(1, items, NOW).by_type["harassment"]
    assert summary.distinct_source_types == 2
    assert summary.corroborated is True


def test_aggregate_single_source_not_corroborated_by_two_items() -> None:
    items = [
        obs(1, "harassment", NOW, source="user_report"),
        obs(1, "harassment", NOW, source="user_report"),
    ]
    summary = aggregate(1, items, NOW).by_type["harassment"]
    assert summary.distinct_source_types == 1
    assert summary.corroborated is False


def test_aggregate_three_items_corroborate_even_single_source() -> None:
    # Independence proxy matches compute_states: >= 3 items corroborate.
    items = [obs(1, "harassment", NOW, source="user_report") for _ in range(3)]
    summary = aggregate(1, items, NOW).by_type["harassment"]
    assert summary.corroborated is True
    assert summary.distinct_source_types == 1


def test_evidence_hash_is_stable_and_content_bound() -> None:
    h1 = evidence_hash(1, "user_report", "harassment", {"severity": 2}, NOW)
    h2 = evidence_hash(1, "user_report", "harassment", {"severity": 2}, NOW)
    h3 = evidence_hash(1, "user_report", "harassment", {"severity": 3}, NOW)
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64


# --- API --------------------------------------------------------------------


def make_evidence_store() -> MemoryEvidenceStore:
    store = MemoryEvidenceStore(
        observations=[
            obs(1, "harassment", NOW - timedelta(hours=3)),
            obs(1, "harassment", NOW - timedelta(hours=5), source="city_data", reliability=0.9),
            obs(1, "streetlight_not_working", NOW - timedelta(days=2), value={"working": False}),
            obs(2, "poor_lighting", NOW - timedelta(days=400)),  # expired
        ],
        segment_ids=[1, 2],
    )
    return store


@pytest.fixture()
def client() -> TestClient:
    app.dependency_overrides[get_evidence_store] = lambda: make_evidence_store()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_evidence_endpoint_returns_aggregate(client: TestClient) -> None:
    resp = client.get("/api/segments/1/evidence")
    assert resp.status_code == 200
    body = resp.json()
    assert body["segment_id"] == 1
    assert body["total_observations"] == 3
    assert body["model_version"] == "evidence-baseline-v1"
    assert "harassment" in body["by_type"]
    assert body["by_type"]["harassment"]["state_counts"]["CORROBORATED"] == 2
    assert 0.0 <= body["overall_confidence"] <= 0.95


def test_evidence_endpoint_never_exposes_identity(client: TestClient) -> None:
    resp = client.get("/api/segments/1/evidence")
    body = resp.json()
    flat = str(body)
    for forbidden in ("reporter", "identity", "description", "user_id", "phone", "email"):
        assert forbidden not in flat.lower()


def test_evidence_endpoint_unknown_segment_is_404(client: TestClient) -> None:
    resp = client.get("/api/segments/999999/evidence")
    assert resp.status_code == 404


def test_evidence_endpoint_empty_segment_is_graceful(client: TestClient) -> None:
    resp = client.get("/api/segments/2/evidence")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_observations"] == 0
    assert body["overall_confidence"] == 0.0
