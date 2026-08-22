from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from app.cv.mock_impl import DevMockCVInferenceService
from app.cv.registry import get_cv_service
from app.main import app

client = TestClient(app)

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture(autouse=True)
def _reset_cv_service_cache() -> None:
    get_cv_service.cache_clear()
    yield
    get_cv_service.cache_clear()


def test_cv_models_lists_registered_checkpoints() -> None:
    resp = client.get("/api/cv/models")
    assert resp.status_code == 200
    body = resp.json()
    names = [m["name"] for m in body["models"]]
    assert "base_model" in names
    assert "faster_rcnn" in names
    assert body["backend"] == "mock"
    assert body["is_real_inference"] is False
    statuses = {m["status"] for m in body["models"]}
    assert statuses == {"VALIDATION_REQUIRED"}


def test_cv_health_reports_mock_with_note() -> None:
    resp = client.get("/api/cv/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["loaded"] is True
    assert body["is_real_inference"] is False
    assert "DEVELOPMENT MOCK" in body["note"]


def test_cv_predict_with_valid_png() -> None:
    resp = client.post(
        "/api/cv/predict",
        json={"image_base64": base64.b64encode(TINY_PNG).decode("ascii"), "kind": "cv_classifier"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["kind"] == "cv_classifier"
    assert len(body["scores"]) == 20
    assert 0.0 <= body["confidence"] <= 1.0
    assert body["is_real_inference"] is False
    assert "MOCK" in body["note"]


def test_cv_predict_rejects_garbage_image_bytes() -> None:
    resp = client.post(
        "/api/cv/predict",
        json={
            "image_base64": base64.b64encode(b"this is not an image").decode("ascii"),
            "kind": "cv_classifier",
        },
    )
    assert resp.status_code == 400
    assert "Invalid input" in resp.json()["detail"]


def test_cv_predict_rejects_unsupported_kind() -> None:
    resp = client.post(
        "/api/cv/predict",
        json={"image_base64": base64.b64encode(TINY_PNG).decode("ascii"), "kind": "cv_detector"},
    )
    assert resp.status_code == 404


def test_cv_predict_with_disabled_backend_returns_503(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "cv_backend", "disabled")
    get_cv_service.cache_clear()
    resp = client.post(
        "/api/cv/predict",
        json={"image_base64": base64.b64encode(TINY_PNG).decode("ascii"), "kind": "cv_classifier"},
    )
    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"].lower()


def test_mock_never_claims_real_inference() -> None:
    service = DevMockCVInferenceService()
    from app.cv.interface import CVInferenceRequest

    prediction = service.predict(
        CVInferenceRequest(image=[[[0.0, 0.0, 0.0]]], kind="cv_classifier")
    )
    assert prediction.is_real_inference is False
    assert "MOCK" in prediction.note
