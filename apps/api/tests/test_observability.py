from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_client_supplied_request_id_is_echoed() -> None:
    resp = client.get("/health", headers={"X-Request-Id": "trace-abc-123"})
    assert resp.status_code == 200
    assert resp.headers["X-Request-Id"] == "trace-abc-123"


def test_request_id_is_generated_when_missing() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    request_id = resp.headers["X-Request-Id"]
    assert request_id
    assert len(request_id) == 32


def test_access_log_contains_request_id_and_status(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="app.access"):
        resp = client.get("/health", headers={"X-Request-Id": "trace-log-1"})
    assert resp.status_code == 200
    records = [r for r in caplog.records if r.name == "app.access"]
    assert any(
        r.getMessage() == "request completed"
        and r.__dict__.get("request_id") == "trace-log-1"
        and r.__dict__.get("status") == 200
        for r in records
    )