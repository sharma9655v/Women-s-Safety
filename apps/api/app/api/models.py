from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.cv.registry import cv_models_metadata
from app.evidence.registry import get_evidence_store
from app.evidence.store import EvidenceStore
from app.schemas import CVModelInfo, MlGate, ModelsCurrentResponse
from app.segments.registry import get_segments_store
from app.segments.store import SegmentStore

router = APIRouter(prefix="/api", tags=["models"])

RISK_MODEL = "deterministic-baseline-v1"
EVIDENCE_MODEL = "evidence-baseline-v1"

# Mirrors ml/ml/gate.py; the API reports the gate from its own DB without
# coupling to the ml/ module. Both constants must stay in sync.
MIN_VERIFIED_OBSERVATIONS = 1_000
MIN_SPAN_DAYS = 90


@router.get("/models/current", response_model=ModelsCurrentResponse)
def models_current(
    evidence: Annotated[EvidenceStore, Depends(get_evidence_store)],
    segments: Annotated[SegmentStore, Depends(get_segments_store)],
) -> ModelsCurrentResponse:
    summary = evidence.verification_summary()
    verified = summary["verified_count"]
    span_days = summary["span_days"]
    gate_open = (
        verified >= MIN_VERIFIED_OBSERVATIONS
        and span_days is not None
        and span_days >= MIN_SPAN_DAYS
    )
    from app.metrics import set_active_model

    set_active_model(RISK_MODEL, gate_open)
    cv_models = [
        CVModelInfo(
            name=m.name,
            version=m.version,
            kind=m.kind,
            framework=m.framework,
            checkpoint_path=m.checkpoint_path,
            input_schema=m.input_schema,
            output_schema=m.output_schema,
            status=m.status,
            metrics=m.metrics,
            dataset_version=m.dataset_version,
            integration=m.integration,
        )
        for m in cv_models_metadata()
    ]
    return ModelsCurrentResponse(
        risk_model=RISK_MODEL,
        evidence_model=EVIDENCE_MODEL,
        dataset_versions=segments.dataset_versions(),
        ml_gate=MlGate(
            open=gate_open,
            verified_observations=verified,
            span_days=span_days,
            min_verified_observations=MIN_VERIFIED_OBSERVATIONS,
            min_span_days=MIN_SPAN_DAYS,
        ),
        cv_models=cv_models,
    )
