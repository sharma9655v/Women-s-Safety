"""Emergency SOS sessions + explicit-consent location sharing (Phase 9).

Integrity rules:
  - Sessions are created ONLY after the client-side countdown completes
    (cancelled SOS never reaches the backend).
  - Duplicate active emergency sessions -> 409 (one at a time).
  - Location sharing requires an explicit start; auto-expires; revocable.
  - All rows are scoped to the pseudonymous X-Client-Id; a different client
    gets 404 for any foreign session id (no enumeration).
  - Notifications are recorded with a real channel status; when no channel is
    configured the UI sees 'no_channel' and must never claim delivery."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth import require_client_id
from app.config import settings
from app.reports.limiter import RateLimiter, get_rate_limiter
from app.safety import (
    EmergencySession,
    EmergencyStore,
    NotificationStore,
    SharingSession,
    get_notification_store,
    get_sessions_store,
)
from app.schemas import (
    EmergencyCreateRequest,
    EmergencyEndRequest,
    EmergencyEndResponse,
    EmergencySessionResponse,
    SharingLocationUpdate,
    SharingSessionResponse,
    SharingStartRequest,
)

router = APIRouter(prefix="/api", tags=["emergency"])


def _emergency_limiter() -> RateLimiter:
    return get_rate_limiter("emergency_ratelimit", settings.emergency_rate_limit_per_hour, 3600)


def _sharing_limiter() -> RateLimiter:
    return get_rate_limiter("sharing_ratelimit", 60, 3600)


def _sharing_update_limiter() -> RateLimiter:
    # Location updates arrive on every GPS fix (watchPosition); a limit this
    # high still bounds abuse while not starving a live session.
    return get_rate_limiter("sharing_update_ratelimit", 600, 3600)


def _notify_status() -> str:
    from app.safety.notifications import expected_notify_status

    return expected_notify_status()


def _emergency_response(session: EmergencySession) -> EmergencySessionResponse:
    return EmergencySessionResponse(
        session_id=session.id,
        status=session.status,
        started_at=session.started_at.isoformat(),
        ended_at=session.ended_at.isoformat() if session.ended_at else None,
        end_reason=session.end_reason,
        latitude=session.latitude,
        longitude=session.longitude,
        last_known_at=session.last_known_at.isoformat() if session.last_known_at else None,
        notified_contact_ids=session.notified_contact_ids,
        notify_status=session.notify_status,
        location_sharing=session.location_sharing,
    )


def _sharing_response(session: SharingSession) -> SharingSessionResponse:
    return SharingSessionResponse(
        session_id=session.id,
        kind=session.kind,
        status=session.status,
        started_at=session.started_at.isoformat(),
        expires_at=session.expires_at.isoformat(),
        stopped_at=session.stopped_at.isoformat() if session.stopped_at else None,
        latitude=session.latitude,
        longitude=session.longitude,
        last_updated_at=session.last_updated_at.isoformat() if session.last_updated_at else None,
        recipient_ids=session.recipient_ids,
    )


def _require_limit(limiter: RateLimiter, cid: str) -> None:
    if not limiter.allow(cid):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many emergency actions")


@router.post(
    "/emergency/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=EmergencySessionResponse,
)
def create_emergency(
    payload: EmergencyCreateRequest,
    request: Request,
    store: Annotated[EmergencyStore, Depends(get_sessions_store)],
    notifications: Annotated[NotificationStore, Depends(get_notification_store)],
    limiter: Annotated[RateLimiter, Depends(_emergency_limiter)],
    cid: Annotated[str, Depends(require_client_id)],
) -> EmergencySessionResponse:
    _require_limit(limiter, cid)
    if store.active_emergency(cid) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An emergency session is already active"
        )
    session = store.create_emergency(
        cid,
        latitude=payload.latitude,
        longitude=payload.longitude,
        notified_contact_ids=payload.notified_contact_ids,
        notify_status=_notify_status(),
    )
    notifications.record(
        cid,
        "sos_started",
        {
            "session_id": session.id,
            "contact_ids": session.notified_contact_ids,
            "notify_status": session.notify_status,
        },
    )
    return _emergency_response(session)


@router.get("/emergency/sessions/active", response_model=EmergencySessionResponse | None)
def active_emergency(
    request: Request,
    store: Annotated[EmergencyStore, Depends(get_sessions_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> EmergencySessionResponse | None:
    session = store.active_emergency(cid)
    return _emergency_response(session) if session is not None else None


@router.post("/emergency/sessions/{session_id}/location", response_model=EmergencySessionResponse)
def update_emergency_location(
    session_id: str,
    payload: SharingLocationUpdate,
    request: Request,
    store: Annotated[EmergencyStore, Depends(get_sessions_store)],
    limiter: Annotated[RateLimiter, Depends(_sharing_update_limiter)],
    cid: Annotated[str, Depends(require_client_id)],
) -> EmergencySessionResponse:
    _require_limit(limiter, cid)
    session = store.update_emergency_location(cid, session_id, payload.latitude, payload.longitude)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown or ended emergency session")
    return _emergency_response(session)


@router.post("/emergency/sessions/{session_id}/end", response_model=EmergencyEndResponse)
def end_emergency(
    session_id: str,
    payload: EmergencyEndRequest,
    request: Request,
    store: Annotated[EmergencyStore, Depends(get_sessions_store)],
    notifications: Annotated[NotificationStore, Depends(get_notification_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> EmergencyEndResponse:
    session = store.end_emergency(cid, session_id, payload.reason)
    if session is None or session.status != "ENDED":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown or ended emergency session")
    notifications.record(
        cid,
        "sos_ended",
        {"session_id": session.id, "reason": session.end_reason},
    )
    return EmergencyEndResponse(
        session_id=session.id,
        status=session.status,
        ended_at=session.ended_at.isoformat() if session.ended_at else "",
        end_reason=session.end_reason or "",
    )


@router.post(
    "/location-sharing",
    status_code=status.HTTP_201_CREATED,
    response_model=SharingSessionResponse,
)
def start_sharing(
    payload: SharingStartRequest,
    request: Request,
    store: Annotated[EmergencyStore, Depends(get_sessions_store)],
    notifications: Annotated[NotificationStore, Depends(get_notification_store)],
    limiter: Annotated[RateLimiter, Depends(_sharing_limiter)],
    cid: Annotated[str, Depends(require_client_id)],
) -> SharingSessionResponse:
    _require_limit(limiter, cid)
    if payload.owner_session is not None:
        emergency = store.get_emergency(cid, payload.owner_session)
        if emergency is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown emergency session")
    ttl_s = min(payload.ttl_s, settings.location_sharing_max_ttl_s)
    session = store.start_sharing(
        cid,
        kind=payload.kind,
        owner_session=payload.owner_session,
        ttl_s=ttl_s,
        recipient_ids=payload.recipient_ids,
    )
    notifications.record(
        cid,
        "location_sharing_started",
        {
            "session_id": session.id,
            "kind": session.kind,
            "expires_at": session.expires_at.isoformat(),
            "recipient_ids": session.recipient_ids,
        },
    )
    return _sharing_response(session)


@router.get("/location-sharing/active", response_model=SharingSessionResponse | None)
def active_sharing(
    request: Request,
    store: Annotated[EmergencyStore, Depends(get_sessions_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> SharingSessionResponse | None:
    session = store.active_sharing(cid)
    return _sharing_response(session) if session is not None else None


@router.get("/location-sharing/{session_id}", response_model=SharingSessionResponse)
def get_sharing(
    session_id: str,
    request: Request,
    store: Annotated[EmergencyStore, Depends(get_sessions_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> SharingSessionResponse:
    session = store.get_sharing(cid, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown sharing session")
    return _sharing_response(session)


@router.post("/location-sharing/{session_id}/location", response_model=SharingSessionResponse)
def update_sharing_location(
    session_id: str,
    payload: SharingLocationUpdate,
    request: Request,
    store: Annotated[EmergencyStore, Depends(get_sessions_store)],
    limiter: Annotated[RateLimiter, Depends(_sharing_update_limiter)],
    cid: Annotated[str, Depends(require_client_id)],
) -> SharingSessionResponse:
    _require_limit(limiter, cid)
    session = store.update_sharing_location(cid, session_id, payload.latitude, payload.longitude)
    if session is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Unknown, ended or expired sharing session"
        )
    return _sharing_response(session)


@router.post("/location-sharing/{session_id}/stop", response_model=SharingSessionResponse)
def stop_sharing(
    session_id: str,
    request: Request,
    store: Annotated[EmergencyStore, Depends(get_sessions_store)],
    notifications: Annotated[NotificationStore, Depends(get_notification_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> SharingSessionResponse:
    session = store.stop_sharing(cid, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown sharing session")
    if session.status == "STOPPED":
        notifications.record(
            cid,
            "location_sharing_stopped",
            {"session_id": session.id, "reason": "ended_by_user"},
        )
    return _sharing_response(session)
