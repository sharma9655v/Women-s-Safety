"""CV inference HTTP endpoints.

Contract:
  GET  /api/cv/models    — registered checkpoints + backend state
  GET  /api/cv/health    — backend health (loaded / real vs mock)
  POST /api/cv/predict   — image inference (base64 JPEG/PNG/WebP)

Honesty rule: the development mock reports is_real_inference=False and a
note explaining that the output is not a real prediction. Nothing in this
module ever claims the mock is a validated model.
"""

from __future__ import annotations

import base64
import time

from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings
from app.cv import preprocess
from app.cv.interface import (
    CVInferenceError,
    CVInferenceRequest,
    CVInferenceService,
    CVInputError,
    CVModelNotFoundError,
    CVTimeoutError,
)
from app.cv.registry import CVBackendUnavailableError, cv_models_metadata, get_cv_service
from app.metrics import (
    record_cv_inference,
    record_cv_load_failure,
    set_cv_backend_loaded,
)
from app.schemas import (
    CVHealthResponse,
    CVListResponse,
    CVModelInfo,
    CVPredictRequest,
    CVPredictResponse,
)

router = APIRouter(prefix="/api/cv", tags=["cv"])

REAL_BACKEND_NOTE = "Real model backend deployed."
MOCK_NOTE = (
    "DEVELOPMENT MOCK backend — no real model inference is performed. "
    "Outputs must be shown as 'model validation in progress', never as real predictions."
)


def _service() -> CVInferenceService:
    try:
        return get_cv_service()
    except CVBackendUnavailableError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"CV inference unavailable: {exc}",
        ) from exc


def _model_info(metadata: object) -> CVModelInfo:
    from app.cv.interface import ModelMetadata

    if not isinstance(metadata, ModelMetadata):
        raise TypeError("expected ModelMetadata")
    return CVModelInfo(
        name=metadata.name,
        version=metadata.version,
        kind=metadata.kind,
        framework=metadata.framework,
        checkpoint_path=metadata.checkpoint_path,
        input_schema=metadata.input_schema,
        output_schema=metadata.output_schema,
        status=metadata.status,
        metrics=metadata.metrics,
        dataset_version=metadata.dataset_version,
        integration=metadata.integration,
    )


@router.get("/models", response_model=CVListResponse)
def cv_models(request: Request) -> CVListResponse:
    registered = [_model_info(m) for m in cv_models_metadata()]
    try:
        service = get_cv_service()
        loaded = service.is_loaded()
        is_real = _is_real_backend(service)
        set_cv_backend_loaded(loaded)
    except CVBackendUnavailableError as exc:
        loaded, is_real = False, False
        record_cv_load_failure(str(exc))
    return CVListResponse(
        models=registered,
        backend=settings.cv_backend,
        loaded=loaded,
        is_real_inference=is_real,
    )


def _is_real_backend(service: CVInferenceService) -> bool:
    """True only when the active service is not the development mock."""
    from app.cv.mock_impl import DevMockCVInferenceService

    return not isinstance(service, DevMockCVInferenceService)


@router.get("/health", response_model=CVHealthResponse)
def cv_health(request: Request) -> CVHealthResponse:
    try:
        service = _service()
        is_real = _is_real_backend(service)
    except HTTPException as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"CV backend unavailable ({settings.cv_backend}): {exc.detail}"
                if isinstance(exc.detail, str)
                else f"CV backend unavailable ({settings.cv_backend})"
            ),
        ) from exc
    return CVHealthResponse(
        backend=settings.cv_backend,
        loaded=service.is_loaded(),
        models=[_model_info(m) for m in cv_models_metadata()],
        is_real_inference=is_real,
        note="" if is_real else MOCK_NOTE,
    )


@router.post(
    "/predict",
    response_model=CVPredictResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid image input"},
        status.HTTP_404_NOT_FOUND: {"description": "Model/checkpoint not found"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Backend unavailable"},
    },
)
def cv_predict(req: CVPredictRequest, request: Request) -> CVPredictResponse:
    service = _service()
    started = time.perf_counter()
    try:
        raw = base64.b64decode(req.image_base64, validate=True)
        preprocess.validate_bytes(raw)
        image = preprocess.decode_and_preprocess(raw)
        prediction = service.predict(CVInferenceRequest(image=image, kind=req.kind, options={}))
    except (CVInputError, ValueError) as exc:
        record_cv_inference(status="invalid_input", duration_s=time.perf_counter() - started)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Invalid input: {exc}") from exc
    except CVModelNotFoundError as exc:
        record_cv_inference(status="model_missing", duration_s=time.perf_counter() - started)
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Model not found: {exc}") from exc
    except CVTimeoutError as exc:
        record_cv_inference(status="timeout", duration_s=time.perf_counter() - started)
        raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
    except CVInferenceError as exc:
        record_cv_inference(status="inference_error", duration_s=time.perf_counter() - started)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Inference failed: {exc}"
        ) from exc
    record_cv_inference(status="ok", duration_s=time.perf_counter() - started)
    return CVPredictResponse(
        kind=prediction.kind,
        scores=prediction.scores,
        detections=prediction.detections,
        confidence=prediction.confidence,
        model_name=prediction.model_name,
        model_version=prediction.model_version,
        is_real_inference=prediction.is_real_inference,
        note=prediction.note,
    )
