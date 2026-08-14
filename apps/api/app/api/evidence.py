from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.evidence import EvidenceStore, aggregate, get_evidence_store
from app.schemas import EvidenceTypeSummary, SegmentEvidenceResponse

router = APIRouter(prefix="/api")


@router.get(
    "/segments/{segment_id}/evidence",
    response_model=SegmentEvidenceResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Unknown segment id"},
    },
)
def segment_evidence(
    segment_id: int,
    store: Annotated[EvidenceStore, Depends(get_evidence_store)],
) -> SegmentEvidenceResponse:
    """Aggregated evidence for one road segment.

    Returns freshness, confidence, per-type scores and conflict flags.
    Never returns reporter identity or report content.
    """
    if not store.segment_exists(segment_id):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Unknown segment id: {segment_id}",
        )

    items = store.observations_for_segment(segment_id)
    evidence = aggregate(segment_id, items)
    return SegmentEvidenceResponse(
        segment_id=evidence.segment_id,
        total_observations=evidence.total_observations,
        overall_freshness=evidence.overall_freshness,
        overall_confidence=evidence.overall_confidence,
        conflicts=evidence.conflicts,
        by_type={t: EvidenceTypeSummary(**asdict(s)) for t, s in evidence.by_type.items()},
        model_version=evidence.model_version,
    )
