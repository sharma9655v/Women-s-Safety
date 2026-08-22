"""Development-only CV inference implementation.

THIS IS A MOCK. It exists so the CV integration architecture (API, schema,
preprocessing, postprocessing, health checks, error handling) is complete and
testable before the ML pipeline produces a validated checkpoint.

It NEVER performs real inference:

  - predictions are deterministic placeholder outputs labelled
    is_real_inference=False with an explicit note;
  - the /api/cv endpoints and the UI must surface that state ("model
    validation in progress") instead of presenting the outputs as real;
  - replacing this mock with a real backend requires only a class that
    implements CVInferenceService and a settings change (CV_BACKEND=real +
    CV_REAL_BACKEND_MODULE) — no caller changes.
"""

from __future__ import annotations

from app.config import settings
from app.cv.interface import (
    CVInferenceRequest,
    CVInferenceService,
    CVModelNotFoundError,
    CVPrediction,
    ModelMetadata,
)
from app.cv.postprocess import aggregate_confidence, normalize_classifier_scores

MOCK_NOTE = (
    "DEVELOPMENT MOCK — no real model inference performed. This output is "
    "not a real prediction and must not be treated as one."
)


class DevMockCVInferenceService(CVInferenceService):
    """Deterministic development mock behind the CVInferenceService contract.

    Reports the same metadata as the registered checkpoint (from
    models/registry.json) but performs no inference. Used when
    CV_BACKEND=mock (the default) and by tests.
    """

    def __init__(
        self,
        *,
        name: str = "base_model",
        version: str = "v1",
        checkpoint_path: str | None = None,
    ) -> None:
        self._name = name
        self._version = version
        self._checkpoint_path = checkpoint_path or settings.cv_model_dir
        self._loaded = True  # a mock is always "available" for integration testing

    def metadata(self) -> ModelMetadata:
        return ModelMetadata(
            name=self._name,
            version=self._version,
            kind="cv_classifier",
            framework="keras",
            checkpoint_path=self._checkpoint_path,
            input_schema={"dtype": "float32", "shape": [None, 360, 640, 3], "format": "RGB"},
            output_schema={
                "units": 20,
                "activation": "sigmoid",
                "task": "multi_label_classification",
            },
            status="VALIDATION_REQUIRED",
            metrics={},
            integration="not_integrated",
        )

    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        self._loaded = True

    def predict(self, request: CVInferenceRequest) -> CVPrediction:
        if request.kind != "cv_classifier":
            raise CVModelNotFoundError(
                f"mock backend only supports cv_classifier, got {request.kind!r}"
            )
        if not request.image:
            raise CVModelNotFoundError("mock backend received an empty image payload")
        # Deterministic placeholder scores: flat across 20 units with a tiny
        # deterministic pattern so output-schema plumbing is exercised.
        height = len(request.image)
        width = len(request.image[0]) if height else 0
        seed = (height + width) % 20
        scores = normalize_classifier_scores(
            [0.5 + 0.001 * ((i + seed) % 7 - 3) for i in range(20)], "sigmoid"
        )
        return CVPrediction(
            kind="cv_classifier",
            scores=scores,
            confidence=aggregate_confidence(scores),
            model_name=self._name,
            model_version=self._version,
            is_real_inference=False,
            note=MOCK_NOTE,
        )
