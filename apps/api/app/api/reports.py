from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from app.config import settings
from app.evidence.registry import get_evidence_store
from app.evidence.states import VerificationState
from app.evidence.store import EvidenceStore
from app.reports import get_reports_store
from app.reports.limiter import RateLimiter, client_key, get_rate_limiter
from app.reports.redact import encrypt_blob, redact_description, strip_image_metadata
from app.reports.spam import DuplicateDetector, get_duplicate_detector, report_key
from app.reports.store import ReportStore
from app.schemas import (
    AdminReport,
    AdminReportListResponse,
    AdminVerificationResponse,
    RecomputeRequest,
    RecomputeResponse,
    ReportRequest,
    ReportResponse,
    QuickReportRequest,
    QuickReportResponse,
)

router = APIRouter(prefix="/api", tags=["reports"])

MODEL_VERSION = "evidence-baseline-v1"

# Development-only fallback, active only when ADMIN_DEV_KEY_ENABLED=1 AND
# APP_ENV=development. Production must set ADMIN_KEY in the environment.
DEV_ADMIN_KEY = "dev-admin-key"


def _parse_image_data(data_url: str) -> bytes:
    try:
        if "," in data_url and data_url.split(",", 1)[0].endswith(";base64"):
            raw = data_url.split(",", 1)[1]
        else:
            raw = data_url
        return base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "evidence_image is not valid base64"
        ) from exc


def _require_admin(x_admin_key: str) -> str:
    """Return the sha256 hash of the accepted admin key (for the audit log)."""
    if settings.admin_key:
        if not secrets.compare_digest(x_admin_key, settings.admin_key):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid admin key")
    elif settings.app_env == "development" and settings.admin_dev_key_enabled:
        if not secrets.compare_digest(x_admin_key, DEV_ADMIN_KEY):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid admin key")
    else:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Admin endpoints disabled")
    return hashlib.sha256(x_admin_key.encode()).hexdigest()


@router.post("/reports", status_code=status.HTTP_201_CREATED, response_model=ReportResponse)
def create_report(
    payload: ReportRequest,
    request: Request,
    evidence: Annotated[EvidenceStore, Depends(get_evidence_store)],
    reports: Annotated[ReportStore, Depends(get_reports_store)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    duplicates: Annotated[DuplicateDetector, Depends(get_duplicate_detector)],
) -> ReportResponse:
    if not evidence.segment_exists(payload.segment_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown segment id: {payload.segment_id}")

    client = client_key(request)
    redacted = redact_description(payload.description) if payload.description is not None else None

    dup_key = report_key(payload.segment_id, payload.category, redacted or "", client)
    if duplicates.is_duplicate(dup_key):
        raise HTTPException(status.HTTP_409_CONFLICT, "Duplicate report — already received")
    if not limiter.allow(client):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many reports — try again later")

    image_encrypted = None
    if payload.evidence_image is not None:
        try:
            stripped = strip_image_metadata(_parse_image_data(payload.evidence_image))
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
        image_encrypted = encrypt_blob(stripped)

    report_id = reports.insert_report(
        segment_id=payload.segment_id,
        category=payload.category,
        description_redacted=redacted,
        client_hash=client,
        image_encrypted=image_encrypted,
    )
    duplicates.record(dup_key)

    return ReportResponse(
        report_id=report_id,
        segment_id=payload.segment_id,
        category=payload.category,
        verification_state="REPORTED",
        model_version=MODEL_VERSION,
    )


@router.post(
    "/reports/quick",
    response_model=QuickReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quick_report(
    payload: QuickReportRequest,
    request: Request,
    evidence: Annotated[EvidenceStore, Depends(get_evidence_store)],
    reports: Annotated[ReportStore, Depends(get_reports_store)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    duplicates: Annotated[DuplicateDetector, Depends(get_duplicate_detector)],
) -> QuickReportResponse:
    if not evidence.segment_exists(payload.segment_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown segment id: {payload.segment_id}")

    client = client_key(request)
    dup_key = report_key(payload.segment_id, payload.category, payload.description or "", client)
    if duplicates.is_duplicate(dup_key):
        raise HTTPException(status.HTTP_409_CONFLICT, "Duplicate report — already received")
    if not limiter.allow(client):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many reports — try again later")

    redacted = redact_description(payload.description) if payload.description is not None else None
    report_id = reports.insert_report(
        segment_id=payload.segment_id,
        category=payload.category,
        description_redacted=redacted,
        client_hash=client,
        image_encrypted=None,
    )
    duplicates.record(dup_key)

    return QuickReportResponse(
        report_id=report_id,
        segment_id=payload.segment_id,
        category=payload.category,
        verification_state="REPORTED",
    )


@router.post("/admin/recompute", response_model=RecomputeResponse)
def recompute(
    payload: RecomputeRequest,
    reports: Annotated[ReportStore, Depends(get_reports_store)],
    x_admin_key: Annotated[str, Header()] = "",
) -> RecomputeResponse:
    """Re-derive verification states from the evidence engine and persist them.

    Deterministic: calling it twice with no new evidence changes nothing.
    """
    admin_hash = _require_admin(x_admin_key)
    if payload.segment_id is not None:
        if not reports.segment_exists(payload.segment_id):
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"Unknown segment id: {payload.segment_id}"
            )
        changed = reports.recompute_segment(payload.segment_id)
        reports.audit(
            "recompute",
            admin_hash,
            {"segment_id": payload.segment_id, "recomputed": changed, "segments": 1},
        )
        return RecomputeResponse(recomputed=changed, segments=1)
    changed, segments = reports.recompute_all()
    reports.audit(
        "recompute",
        admin_hash,
        {"segment_id": None, "recomputed": changed, "segments": segments},
    )
    return RecomputeResponse(recomputed=changed, segments=segments)


@router.get("/admin/reports", response_model=AdminReportListResponse)
def list_reports_for_review(
    reports: Annotated[ReportStore, Depends(get_reports_store)],
    x_admin_key: Annotated[str, Header()] = "",
    limit: int = Query(default=50, ge=1, le=200),
) -> AdminReportListResponse:
    """Admin review queue: verification states only.

    Privacy contract: report content (description, image, client hash) is
    never returned — an operator sees id/segment/category/state/date only.
    """
    _require_admin(x_admin_key)
    return AdminReportListResponse(
        reports=[
            AdminReport(
                report_id=report.id,
                segment_id=report.segment_id,
                category=report.category,
                verification_state=report.verification_state.value,
                reported_at=report.reported_at.isoformat(),
                confidence=report.confidence,
            )
            for report in reports.list_reports(limit)
        ]
    )


@router.post(
    "/admin/reports/{report_id}/verify",
    response_model=AdminVerificationResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Unknown report id"},
    },
)
def verify_report(
    report_id: int,
    reports: Annotated[ReportStore, Depends(get_reports_store)],
    x_admin_key: Annotated[str, Header()] = "",
) -> AdminVerificationResponse:
    """Manually mark a report VERIFIED (sticky in the state machine).

    The segment is recomputed afterwards so sibling observations reconcile;
    the decision is audited with the admin key hash.
    """
    return _set_verification(report_id, VerificationState.VERIFIED, "verify", reports, x_admin_key)


@router.post(
    "/admin/reports/{report_id}/reject",
    response_model=AdminVerificationResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Unknown report id"},
    },
)
def reject_report(
    report_id: int,
    reports: Annotated[ReportStore, Depends(get_reports_store)],
    x_admin_key: Annotated[str, Header()] = "",
) -> AdminVerificationResponse:
    """Manually mark a report REJECTED (sticky; excluded from scoring).

    Same recompute + audit contract as verify.
    """
    return _set_verification(
        report_id, VerificationState.REJECTED, "reject", reports, x_admin_key
    )


def _set_verification(
    report_id: int,
    state: VerificationState,
    action: str,
    reports: ReportStore,
    x_admin_key: str,
) -> AdminVerificationResponse:
    admin_hash = _require_admin(x_admin_key)
    report = reports.set_verification(report_id, state)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown report id: {report_id}")
    # VERIFIED/REJECTED are sticky in the state machine; recompute reconciles
    # sibling observations on the same segment afterwards.
    reports.recompute_segment(report.segment_id)
    reports.audit(action, admin_hash, {"report_id": report_id, "state": state.value})
    return AdminVerificationResponse(report_id=report_id, verification_state=state.value)
