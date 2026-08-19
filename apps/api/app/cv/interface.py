"""CV inference interface.

The application depends on these abstractions, never on a concrete model file.
A future real model backend (Keras/TensorFlow/PyTorch) implements
CVInferenceService without touching callers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class CVInferenceError(Exception):
    """Base error for CV inference failures."""


class CVModelNotFoundError(CVInferenceError):
    """The configured checkpoint is missing or unreadable."""


class CVInputError(CVInferenceError):
    """The submitted input (image, size, encoding) is invalid."""


class CVTimeoutError(CVInferenceError):
    """Inference exceeded the configured timeout."""


@dataclass(frozen=True)
class ModelMetadata:
    """Machine-readable metadata for one checkpoint.

    status uses the registry vocabulary: AVAILABLE, EXPERIMENTAL,
    VALIDATION_REQUIRED, PRODUCTION. An unvalidated checkpoint must never be
    reported as PRODUCTION.
    """

    name: str
    version: str
    kind: str  # cv_classifier | cv_detector | risk_model | evidence_model
    framework: str
    checkpoint_path: str
    input_schema: dict[str, object]
    output_schema: dict[str, object]
    status: str
    metrics: dict[str, float] = field(default_factory=dict)
    dataset_version: str | None = None
    integration: str = "not_integrated"


@dataclass(frozen=True)
class CVInferenceRequest:
    """Preprocessed input to an inference call."""

    # RGB float array, normalized to [0, 1], shape (H, W, 3).
    image: list[list[list[float]]]
    kind: str  # cv_classifier | cv_detector
    options: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CVPrediction:
    """Normalized inference output.

    For classifiers: scores is one float per output unit.
    For detectors: detections carries normalized boxes + class indices.
    confidence is always an aggregate in [0, 1]; None when the backend cannot
    produce a meaningful value.
    """

    kind: str
    scores: list[float] = field(default_factory=list)
    detections: list[dict[str, object]] = field(default_factory=list)
    confidence: float | None = None
    model_name: str = ""
    model_version: str = ""
    is_real_inference: bool = False
    note: str = ""


class CVInferenceService(ABC):
    """Contract every CV backend implements."""

    @abstractmethod
    def metadata(self) -> ModelMetadata:
        """Metadata of the loaded checkpoint (or the configured one)."""

    @abstractmethod
    def is_loaded(self) -> bool:
        """True when a checkpoint is loaded and ready for inference."""

    @abstractmethod
    def load(self) -> None:
        """Load the checkpoint. Raises CVModelNotFoundError on failure."""

    @abstractmethod
    def predict(self, request: CVInferenceRequest) -> CVPrediction:
        """Run inference on one preprocessed input.

        Raises CVInferenceError (CVInputError / CVTimeoutError /
        CVModelNotFoundError) on failure. May run synchronously; backends
        with blocking calls should document it.
        """
