from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.evidence.engine import Observation
from app.evidence.states import VerificationState
from app.main import app


def _client() -> tuple[TestClient, object]:
    from app.evidence import MemoryEvidenceStore
    from app.evidence.registry import get_evidence_store
    from app.segments.registry import get_segments_store
    from app.segments.store import MemorySegmentStore

    app.dependency_overrides = {}
    evidence = MemoryEvidenceStore(segment_ids=[456736])
    segments = MemorySegmentStore([])
    app.dependency_overrides[get_evidence_store] = lambda: evidence
    app.dependency_overrides[get_segments_store] = lambda: segments
    return TestClient(app), evidence


def test_models_current_reports_gate_closed() -> None:
    client, evidence = _client()
    now = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    evidence._observations.extend(  # type: ignore[attr-defined]
        [
            Observation(
                segment_id=456736,
                source_type="city_data",
                observation_type="streetlight_not_working",
                observed_at=now,
                source_reliability=0.9,
                value={"working": True},
                state=VerificationState.VERIFIED,
                id=1,
            )
        ]
    )
    resp = client.get("/api/models/current")
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk_model"] == "deterministic-baseline-v1"
    assert body["evidence_model"] == "evidence-baseline-v1"
    assert body["ml_gate"]["open"] is False
    assert body["ml_gate"]["verified_observations"] == 1
    assert body["ml_gate"]["min_verified_observations"] == 1000
    assert body["ml_gate"]["min_span_days"] == 90


def test_models_current_gate_open_when_thresholds_met() -> None:
    client, evidence = _client()
    t0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    evidence._observations.extend(  # type: ignore[attr-defined]
        [
            Observation(
                segment_id=456736,
                source_type="street_audit",
                observation_type="streetlight_not_working",
                observed_at=t0 + timedelta(days=100 * (i // 10)),
                source_reliability=0.95,
                value={"working": True},
                state=VerificationState.VERIFIED,
                id=i + 1,
            )
            for i in range(1000)
        ]
    )
    body = client.get("/api/models/current").json()
    assert body["ml_gate"]["verified_observations"] == 1000
    assert body["ml_gate"]["span_days"] >= 90
    assert body["ml_gate"]["open"] is True
