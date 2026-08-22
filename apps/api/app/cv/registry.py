"""CV service factory + model registry access.

- models/registry.json holds every registered checkpoint with status
  (AVAILABLE / EXPERIMENTAL / VALIDATION_REQUIRED / PRODUCTION). An
  unvalidated checkpoint is never PRODUCTION.
- get_cv_service() builds the CVInferenceService configured by settings:
    * CV_BACKEND=mock  -> DevMockCVInferenceService (default, clearly labelled)
    * CV_BACKEND=disabled -> raises (API returns 503)
    * CV_BACKEND=real  -> imports settings.cv_real_backend_module and uses
      its service; raises if the module is not configured/deployable.
"""

from __future__ import annotations

import importlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import settings
from app.cv.interface import CVInferenceService, CVModelNotFoundError, ModelMetadata
from app.cv.mock_impl import DevMockCVInferenceService

# Status vocabulary (model-registry contract). Never report an unvalidated
# checkpoint as PRODUCTION.
MODEL_STATUSES = ("AVAILABLE", "EXPERIMENTAL", "VALIDATION_REQUIRED", "PRODUCTION")

def _find_repo_root() -> Path:
    """Walk up from this file to the directory holding models/registry.json.

    In a normal checkout this resolves to the repository root. In containers
    only the app package is copied to /app (models/ stays outside the build
    context), so no ancestor matches and we fall back to the working
    directory; load_registry() then reports an empty registry instead of
    crashing at import time.
    """
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "models" / "registry.json").is_file():
            return ancestor
    return Path.cwd()


REPO_ROOT = _find_repo_root()
REGISTRY_PATH = REPO_ROOT / "models" / "registry.json"

CV_CLASSIFIER_STATUS_FALLBACK = "VALIDATION_REQUIRED"


class CVBackendUnavailableError(RuntimeError):
    """The configured CV backend cannot be used (disabled or misconfigured)."""


def _registry_path() -> Path:
    configured = Path(settings.cv_model_dir)
    if configured.is_absolute():
        return configured / "registry.json"
    return REPO_ROOT / configured / "registry.json"


def load_registry(path: Path | None = None) -> dict[str, Any]:
    """Read models/registry.json. Missing file -> empty registry (the API
    then reports that no checkpoints are registered)."""
    registry_path = path or _registry_path()
    if not registry_path.exists():
        return {"schema_version": 1, "models": []}
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"schema_version": 1, "models": []}
    return payload


def list_registered_models(path: Path | None = None) -> list[dict[str, Any]]:
    registry = load_registry(path)
    return list(registry.get("models", []))


def cv_models_metadata() -> list[ModelMetadata]:
    """Registered CV checkpoints as ModelMetadata objects. Unreadable or
    schema-invalid entries are skipped (startup validation reports them)."""
    result: list[ModelMetadata] = []
    for entry in list_registered_models():
        kind = entry.get("kind", "")
        if not kind.startswith("cv_"):
            continue
        status = entry.get("status", CV_CLASSIFIER_STATUS_FALLBACK)
        if status not in MODEL_STATUSES:
            status = CV_CLASSIFIER_STATUS_FALLBACK
        result.append(
            ModelMetadata(
                name=str(entry.get("name", "unnamed")),
                version=str(entry.get("version", "unknown")),
                kind=kind,
                framework=str(entry.get("framework", "unknown")),
                checkpoint_path=str(entry.get("checkpoint_path", "")),
                input_schema=dict(entry.get("input_schema", {})),
                output_schema=dict(entry.get("output_schema", {})),
                status=status,
                metrics=dict(entry.get("metrics", {})),
                dataset_version=entry.get("dataset_version"),
                integration=str(entry.get("integration", "not_integrated")),
            )
        )
    return result


@lru_cache(maxsize=1)
def get_cv_service() -> CVInferenceService:
    """Build the configured CV inference service (cached per process).

    Raises CVBackendUnavailableError when the backend is disabled or a real
    backend module is requested but not configured — callers (the /api/cv
    router) turn that into HTTP 503.
    """
    backend = settings.cv_backend.strip().lower()
    if backend == "disabled":
        raise CVBackendUnavailableError("CV inference is disabled (CV_BACKEND=disabled)")
    if backend == "mock":
        service = DevMockCVInferenceService()
        service.load()
        return service
    if backend == "real":
        module_name = settings.cv_real_backend_module.strip()
        if not module_name:
            raise CVBackendUnavailableError(
                "CV_BACKEND=real requires CV_REAL_BACKEND_MODULE to be set"
            )
        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:
            raise CVBackendUnavailableError(
                f"real CV backend module {module_name!r} is not importable: {exc}"
            ) from exc
        factory = getattr(module, "build_service", None)
        if not callable(factory):
            raise CVBackendUnavailableError(
                f"real CV backend module {module_name!r} must expose build_service()"
            )
        service = factory()
        loaded_service: CVInferenceService = service
        try:
            loaded_service.load()
        except CVModelNotFoundError as exc:
            raise CVBackendUnavailableError(f"real CV backend failed to load: {exc}") from exc
        if not loaded_service.is_loaded():
            raise CVBackendUnavailableError("real CV backend reported not loaded after load()")
        return loaded_service
    raise CVBackendUnavailableError(f"unknown CV_BACKEND {settings.cv_backend!r}")
