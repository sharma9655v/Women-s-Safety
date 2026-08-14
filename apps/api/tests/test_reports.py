import base64
import hashlib
import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.evidence.engine import Observation
from app.evidence.states import VerificationState
from app.main import app

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
PNG_B64 = base64.b64encode(PNG_1PX).decode()


def make_client(
    *, limit: int = 5, duplicate_window_s: int = 3600
) -> tuple[TestClient, object, object]:
    from app.evidence import MemoryEvidenceStore
    from app.evidence.registry import get_evidence_store
    from app.reports import get_reports_store
    from app.reports.limiter import MemoryRateLimiter, get_rate_limiter
    from app.reports.spam import MemoryDuplicateDetector, get_duplicate_detector
    from app.reports.store import MemoryReportStore

    app.dependency_overrides = {}
    evidence = MemoryEvidenceStore(segment_ids=[456736, 457230])
    reports = MemoryReportStore(evidence)
    limiter = MemoryRateLimiter(limit, 3600)
    duplicates = MemoryDuplicateDetector(duplicate_window_s)

    app.dependency_overrides[get_evidence_store] = lambda: evidence
    app.dependency_overrides[get_reports_store] = lambda: reports
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    app.dependency_overrides[get_duplicate_detector] = lambda: duplicates
    return TestClient(app), evidence, reports


VALID = {"segment_id": 456736, "category": "harassment", "description": "Man following me"}


def test_report_created_and_content_free() -> None:
    client, _, _ = make_client()
    resp = client.post("/api/reports", json=VALID)
    assert resp.status_code == 201
    body = resp.json()
    assert body["report_id"] >= 1
    assert body["segment_id"] == 456736
    assert body["category"] == "harassment"
    assert body["verification_state"] == "REPORTED"
    assert body["model_version"] == "evidence-baseline-v1"
    flat = json.dumps(body).lower()
    for banned in ("description", "email", "phone", "identity", "ip", "image", "reporter"):
        assert banned not in flat


def test_report_unknown_segment_404() -> None:
    client, _, _ = make_client()
    resp = client.post("/api/reports", json={"segment_id": 999999999, "category": "other"})
    assert resp.status_code == 404


def test_report_invalid_category_422() -> None:
    client, _, _ = make_client()
    resp = client.post("/api/reports", json={"segment_id": 456736, "category": "alien_sighting"})
    assert resp.status_code == 422


def test_description_redacted_before_storage() -> None:
    client, _, reports = make_client()
    dirty = "call +91 98765 43210 or me@example.com now! http://evil.io/x?y=1"
    resp = client.post(
        "/api/reports",
        json={"segment_id": 456736, "category": "other", "description": dirty},
    )
    assert resp.status_code == 201
    stored = next(iter(reports._reports.values()))  # type: ignore[attr-defined]
    redacted = stored.description_redacted
    assert redacted is not None
    for fragment in ("98765", "@", "http", "www", "."):
        assert fragment not in redacted
    assert redacted.count("[redacted]") == 3


def test_duplicate_report_409() -> None:
    client, _, _ = make_client()
    assert client.post("/api/reports", json=VALID).status_code == 201
    dup = client.post("/api/reports", json=VALID)
    assert dup.status_code == 409
    assert "Duplicate" in dup.json()["detail"]


def test_rate_limit_429() -> None:
    client, _, _ = make_client(limit=2)
    for i in range(2):
        payload = {**VALID, "description": f"report number {i}"}
        assert client.post("/api/reports", json=payload).status_code == 201
    resp = client.post(
        "/api/reports",
        json={**VALID, "description": "a different report"},
    )
    assert resp.status_code == 429


def test_image_stripped_and_encrypted() -> None:
    client, _, reports = make_client()
    resp = client.post(
        "/api/reports",
        json={"segment_id": 456736, "category": "road_hazard", "evidence_image": PNG_B64},
    )
    assert resp.status_code == 201
    stored = next(iter(reports._reports.values()))  # type: ignore[attr-defined]
    blob = stored.image_encrypted
    assert blob is not None
    assert blob != PNG_1PX
    from app.reports.redact import decrypt_blob

    assert decrypt_blob(blob).startswith(b"\x89PNG")


def test_invalid_image_422() -> None:
    client, _, _ = make_client()
    bad = base64.b64encode(b"definitely not an image").decode()
    resp = client.post(
        "/api/reports", json={"segment_id": 456736, "category": "other", "evidence_image": bad}
    )
    assert resp.status_code == 422


def test_bad_base64_422() -> None:
    client, _, _ = make_client()
    resp = client.post(
        "/api/reports",
        json={"segment_id": 456736, "category": "other", "evidence_image": "!!not-base64!!"},
    )
    assert resp.status_code == 422


def test_recompute_deterministic(monkeypatch) -> None:
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    client, evidence, reports = make_client()
    evidence._observations.extend(  # type: ignore[attr-defined]
        [
            Observation(
                segment_id=456736,
                source_type="city_data",
                observation_type="poor_lighting",
                observed_at=now,
                source_reliability=0.9,
                value={"poor": True},
                state=VerificationState.REPORTED,
                id=1,
            ),
            Observation(
                segment_id=456736,
                source_type="street_audit",
                observation_type="poor_lighting",
                observed_at=now,
                source_reliability=0.95,
                value={"poor": False},
                state=VerificationState.REPORTED,
                id=2,
            ),
        ]
    )
    reports.insert_report(456736, "poor_lighting", "dark street", "client-1", None)

    no_key = client.post("/api/admin/recompute", json={})
    assert no_key.status_code == 403

    resp = client.post("/api/admin/recompute", json={}, headers={"X-Admin-Key": "dev-admin-key"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["segments"] == 1
    assert body["recomputed"] >= 1

    again = client.post("/api/admin/recompute", json={}, headers={"X-Admin-Key": "dev-admin-key"})
    assert again.json()["recomputed"] == 0

    stored = next(iter(reports._reports.values()))  # type: ignore[attr-defined]
    # The report itself carries no structured value, so it corroborates with the
    # two contradicting observations instead of conflicting with them.
    assert stored.verification_state == "CORROBORATED"


def test_recompute_unknown_segment_404() -> None:
    client, _, _ = make_client()
    resp = client.post(
        "/api/admin/recompute",
        json={"segment_id": 999999999},
        headers={"X-Admin-Key": "dev-admin-key"},
    )
    assert resp.status_code == 404


def test_recompute_writes_audit_log() -> None:
    client, _, reports = make_client()
    client.post("/api/admin/recompute", json={}, headers={"X-Admin-Key": "dev-admin-key"})
    log = reports._audit_log  # type: ignore[attr-defined]
    assert len(log) == 1
    entry = log[0]
    assert entry["action"] == "recompute"
    assert entry["admin_hash"] == hashlib.sha256(b"dev-admin-key").hexdigest()
    assert "recomputed" in entry["details"]
    # The raw key must never be stored.
    assert "dev-admin-key" not in entry["details"].values()

    bad = client.post("/api/admin/recompute", json={}, headers={"X-Admin-Key": "wrong"})
    assert bad.status_code == 403
    assert len(log) == 1  # failed attempts are not audited (no accepted key)


def test_admin_disabled_in_production(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "app_env", "production")
    client, _, _ = make_client()
    resp = client.post("/api/admin/recompute", json={}, headers={"X-Admin-Key": "dev-admin-key"})
    assert resp.status_code == 503
