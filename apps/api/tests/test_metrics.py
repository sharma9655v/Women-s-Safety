from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.metrics import MetricsStore, get_metrics, record_cv_inference, record_request

client = TestClient(app)


def test_metrics_renders_prometheus_text() -> None:
    store = MetricsStore()
    store.incr("test_counter_total")
    store.observe("test_latency_seconds", 0.02)
    store.set_gauge("test_gauge", 1.0)
    rendered = store.render()
    assert "# TYPE test_counter_total counter" in rendered
    assert "test_counter_total 1" in rendered
    assert "test_latency_seconds_count 1" in rendered
    assert 'test_latency_seconds_bucket{le="0.025"} 1' in rendered
    assert "# TYPE test_gauge gauge" in rendered
    assert "test_gauge 1.0" in rendered


def test_metrics_never_contains_pii() -> None:
    record_request(path="/api/routes?secret=abc", method="GET", status_code=200, duration_s=0.01)
    rendered = get_metrics().render()
    # The query string must be stripped from the recorded path label — no
    # `?secret=...` may ever reach the metrics output.
    assert "/api/routes?secret=abc" not in rendered
    assert "?secret=" not in rendered
    assert 'path="/api/routes"' in rendered


def test_cv_metrics_recorded() -> None:
    record_cv_inference(status="ok", duration_s=0.5)
    rendered = get_metrics().render()
    assert 'cv_inference_total{status="ok"}' in rendered
    assert "cv_inference_duration_seconds_count" in rendered


def test_metrics_endpoint_exposed() -> None:
    # The ml_gate gauge is set by the models endpoint; clear any dependency
    # overrides left by other test modules and use isolated in-memory stores.
    from app.evidence import MemoryEvidenceStore
    from app.evidence.registry import get_evidence_store
    from app.segments.registry import get_segments_store
    from app.segments.store import MemorySegmentStore

    app.dependency_overrides = {}
    app.dependency_overrides[get_evidence_store] = lambda: MemoryEvidenceStore([])
    app.dependency_overrides[get_segments_store] = lambda: MemorySegmentStore([])

    resp = client.get("/api/models/current")
    assert resp.status_code == 200

    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "api_requests_total" in resp.text
    assert "ml_gate_open" in resp.text
    assert "active_risk_model" in resp.text


def test_metrics_histogram_bucket_boundaries() -> None:
    store = MetricsStore()
    store.observe("bucket_test_seconds", 0.01)  # exact bucket edge
    store.observe("bucket_test_seconds", 50.0)  # +Inf
    rendered = store.render()
    assert 'bucket_test_seconds_bucket{le="0.01"} 1' in rendered
    assert 'bucket_test_seconds_bucket{le="+Inf"} 1' in rendered
