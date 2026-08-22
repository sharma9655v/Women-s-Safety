"""Guardian journeys (Phase 10): check-ins with staged escalation and
deviation detection against the planned geometry.

Rules:
  - One active guardian session per client (duplicate -> 409).
  - Missed check-ins escalate in stages (checkin_missed, then
    checkin_escalated); with settings.guardian_auto_sos enabled an emergency
    session is auto-started at stage 2 — otherwise the UI surfaces helplines.
  - Deviation is detected only against the geometry the owner provided.
  - Foreign sessions return 404 (no enumeration)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth import require_client_id
from app.config import settings
from app.identity import client_hash
from app.reports.limiter import RateLimiter, get_rate_limiter
from app.safety import (
    EmergencyStore,
    GuardianSession,
    GuardianStore,
    JourneyCheckinStore,
    NotificationStore,
    get_guardian_store,
    get_journey_checkin_store,
    get_notification_store,
    get_sessions_store,
)
from app.safety.journey_checkin import JourneyCheckinSession
from app.schemas import (
    GuardianCreateRequest,
    GuardianEndRequest,
    GuardianEndResponse,
    GuardianSessionResponse,
    JourneyCheckinCreate,
    JourneyCheckinResponse,
    JourneyEndRequest,
    JourneyEndResponse,
    SharingLocationUpdate,
)

router = APIRouter(prefix="/api", tags=["guardian"])


def _guardian_limiter() -> RateLimiter:
    return get_rate_limiter("guardian_ratelimit", 10, 3600)


def _journey_checkin_limiter() -> RateLimiter:
    return get_rate_limiter("journey_checkin_ratelimit", 10, 3600)


def _guardian_location_limiter() -> RateLimiter:
    # GPS fixes arrive continuously while a journey is active; high enough to
    # never starve a live session, low enough to bound abuse.
    return get_rate_limiter("guardian_location_ratelimit", 600, 3600)


def _require_limit(limiter: RateLimiter, cid: str) -> None:
    if not limiter.allow(client_hash(cid)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many journey check-ins")


def _guardian_response(session: GuardianSession) -> GuardianSessionResponse:
    return GuardianSessionResponse(
        session_id=session.id,
        status=session.status,
        started_at=session.started_at.isoformat(),
        ended_at=session.ended_at.isoformat() if session.ended_at else None,
        end_reason=session.end_reason,
        guardian_contact_ids=session.guardian_contact_ids,
        expected_arrival_at=session.expected_arrival_at.isoformat()
        if session.expected_arrival_at
        else None,
        checkin_deadline=session.checkin_deadline.isoformat(),
        checkin_grace_s=session.checkin_grace_s,
        last_checkin_at=session.last_checkin_at.isoformat() if session.last_checkin_at else None,
        latitude=session.latitude,
        longitude=session.longitude,
        last_known_at=session.last_known_at.isoformat() if session.last_known_at else None,
        deviation_detected=session.deviation_detected,
        first_deviation_at=session.first_deviation_at.isoformat()
        if session.first_deviation_at
        else None,
        escalation_stage=session.escalation_stage,
    )


def _emit(
    notifications: NotificationStore, cid: str, events: list[tuple[str, dict[str, object]]]
) -> None:
    for event_type, payload in events:
        notifications.record(cid, event_type, payload)


def _notify_status() -> str:
    from app.safety.notifications import expected_notify_status

    return expected_notify_status()


def _maybe_auto_sos(
    events: list[tuple[str, dict[str, object]]],
    sessions_store: EmergencyStore,
    notifications: NotificationStore,
    cid: str,
) -> None:
    """When a check-in escalates AND auto-SOS is enabled for this deployment,
    start a real emergency session. Honest: status reflects the actual channel."""
    if not settings.guardian_auto_sos:
        return
    if not any(event_type == "checkin_escalated" for event_type, _ in events):
        return
    if sessions_store.active_emergency(cid) is not None:
        return
    session = sessions_store.create_emergency(
        cid,
        latitude=None,
        longitude=None,
        notified_contact_ids=[],
        notify_status=_notify_status(),
    )
    notifications.record(
        cid,
        "sos_started",
        {
            "session_id": session.id,
            "contact_ids": [],
            "notify_status": session.notify_status,
            "trigger": "guardian_escalation",
        },
    )


@router.post(
    "/guardian/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=GuardianSessionResponse,
)
def create_guardian_session(
    payload: GuardianCreateRequest,
    request: Request,
    store: Annotated[GuardianStore, Depends(get_guardian_store)],
    notifications: Annotated[NotificationStore, Depends(get_notification_store)],
    limiter: Annotated[RateLimiter, Depends(_guardian_limiter)],
    cid: Annotated[str, Depends(require_client_id)],
) -> GuardianSessionResponse:
    if not limiter.allow(cid):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many guardian sessions")
    if store.active_guardian(cid)[0] is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A guardian session is already active")
    geometry: list[tuple[float, float]] | None = None
    if payload.planned_geometry:
        geometry = [(float(lon), float(lat)) for lon, lat in payload.planned_geometry]
    session = store.create_guardian(
        cid,
        guardian_contact_ids=payload.guardian_contact_ids,
        expected_arrival_at=payload.expected_arrival_at,
        planned_geometry=geometry,
        checkin_grace_s=payload.checkin_grace_s,
    )
    notifications.record(
        cid,
        "guardian_started",
        {
            "session_id": session.id,
            "contact_ids": session.guardian_contact_ids,
            "deadline": session.checkin_deadline.isoformat(),
        },
    )
    return _guardian_response(session)


@router.get("/guardian/sessions/active", response_model=GuardianSessionResponse | None)
def active_guardian_session(
    request: Request,
    store: Annotated[GuardianStore, Depends(get_guardian_store)],
    notifications: Annotated[NotificationStore, Depends(get_notification_store)],
    sessions_store: Annotated[EmergencyStore, Depends(get_sessions_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> GuardianSessionResponse | None:
    session, events = store.active_guardian(cid)
    _emit(notifications, cid, events)
    _maybe_auto_sos(events, sessions_store, notifications, cid)
    return _guardian_response(session) if session is not None else None


@router.get("/guardian/sessions/{session_id}", response_model=GuardianSessionResponse)
def get_guardian_session(
    session_id: str,
    request: Request,
    store: Annotated[GuardianStore, Depends(get_guardian_store)],
    notifications: Annotated[NotificationStore, Depends(get_notification_store)],
    sessions_store: Annotated[EmergencyStore, Depends(get_sessions_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> GuardianSessionResponse:
    session, events = store.get_guardian(cid, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown guardian session")
    _emit(notifications, cid, events)
    _maybe_auto_sos(events, sessions_store, notifications, cid)
    return _guardian_response(session)


@router.post("/guardian/sessions/{session_id}/location", response_model=GuardianSessionResponse)
def update_guardian_location(
    session_id: str,
    payload: SharingLocationUpdate,
    request: Request,
    store: Annotated[GuardianStore, Depends(get_guardian_store)],
    notifications: Annotated[NotificationStore, Depends(get_notification_store)],
    sessions_store: Annotated[EmergencyStore, Depends(get_sessions_store)],
    limiter: Annotated[RateLimiter, Depends(_guardian_location_limiter)],
    cid: Annotated[str, Depends(require_client_id)],
) -> GuardianSessionResponse:
    if not limiter.allow(cid):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many guardian location updates")
    session, events = store.update_guardian_location(
        cid, session_id, payload.latitude, payload.longitude
    )
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown or ended guardian session")
    _emit(notifications, cid, events)
    _maybe_auto_sos(events, sessions_store, notifications, cid)
    return _guardian_response(session)


@router.post("/guardian/sessions/{session_id}/checkin", response_model=GuardianSessionResponse)
def checkin_guardian(
    session_id: str,
    request: Request,
    store: Annotated[GuardianStore, Depends(get_guardian_store)],
    notifications: Annotated[NotificationStore, Depends(get_notification_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> GuardianSessionResponse:
    session, events = store.checkin(cid, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown or ended guardian session")
    _emit(notifications, cid, events)
    return _guardian_response(session)


@router.post("/guardian/sessions/{session_id}/end", response_model=GuardianEndResponse)
def end_guardian_session(
    session_id: str,
    payload: GuardianEndRequest,
    request: Request,
    store: Annotated[GuardianStore, Depends(get_guardian_store)],
    notifications: Annotated[NotificationStore, Depends(get_notification_store)],
    sessions_store: Annotated[EmergencyStore, Depends(get_sessions_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> GuardianEndResponse:
    session, events = store.end_guardian(cid, session_id, payload.reason)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown or ended guardian session")
    _emit(notifications, cid, events)
    ended_at = session.ended_at.isoformat() if session.ended_at else ""
    if payload.reason == "arrived":
        notifications.record(
            cid,
            "journey_completed",
            {"session_id": session.id, "ended_at": ended_at},
        )
    else:
        notifications.record(
            cid,
            "guardian_ended",
            {"session_id": session.id, "reason": payload.reason},
        )
    return GuardianEndResponse(
        session_id=session.id,
        status=session.status,
        ended_at=ended_at,
        end_reason=session.end_reason or "",
    )


def _journey_checkin_response(session: JourneyCheckinSession) -> JourneyCheckinResponse:
    return JourneyCheckinResponse(
        session_id=session.id,
        status=session.status,
        started_at=session.started_at.isoformat(),
        ended_at=session.ended_at.isoformat() if session.ended_at else None,
        end_reason=session.end_reason,
        destination_name=session.destination_name or "",
        destination_lat=session.destination_lat,
        destination_lon=session.destination_lon,
        expected_arrival_at=(
            session.expected_arrival_at.isoformat() if session.expected_arrival_at else None
        ),
        checkin_interval_s=session.checkin_interval_s,
        checkin_grace_s=session.checkin_grace_s,
        last_checkin_at=session.last_checkin_at.isoformat() if session.last_checkin_at else None,
        next_checkin_at=session.next_checkin_at.isoformat() if session.next_checkin_at else None,
        contact_ids=session.contact_ids,
        escalation_stage=session.escalation_stage,
        notified_stage=session.notified_stage,
        latitude=session.latitude,
        longitude=session.longitude,
        last_known_at=session.last_known_at.isoformat() if session.last_known_at else None,
    )


@router.post(
    "/journey/checkins",
    response_model=JourneyCheckinResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_journey_checkin(
    payload: JourneyCheckinCreate,
    request: Request,
    store: Annotated[JourneyCheckinStore, Depends(get_journey_checkin_store)],
    notifications: Annotated[NotificationStore, Depends(get_notification_store)],
    limiter: Annotated[RateLimiter, Depends(_journey_checkin_limiter)],
    cid: Annotated[str, Depends(require_client_id)],
) -> JourneyCheckinResponse:
    _require_limit(limiter, cid)
    session = store.create_journey_checkin(
        cid,
        destination_name=payload.destination_name,
        destination_lat=payload.destination_lat,
        destination_lon=payload.destination_lon,
        expected_arrival_at=payload.expected_arrival_at,
        checkin_interval_s=payload.checkin_interval_s,
        checkin_grace_s=payload.checkin_grace_s,
        contact_ids=payload.contact_ids,
    )
    notifications.record(
        cid,
        "checkin_reminder",
        {
            "session_id": session.id,
            "destination": payload.destination_name,
        },
    )
    return _journey_checkin_response(session)


@router.get(
    "/journey/checkins/active",
    response_model=JourneyCheckinResponse | None,
)
def active_journey_checkin(
    request: Request,
    store: Annotated[JourneyCheckinStore, Depends(get_journey_checkin_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> JourneyCheckinResponse | None:
    session = store.active_journey_checkin(cid)
    return _journey_checkin_response(session) if session is not None else None


@router.post(
    "/journey/checkins/{session_id}/checkin",
    response_model=JourneyCheckinResponse,
)
def checkin_journey(
    session_id: str,
    request: Request,
    store: Annotated[JourneyCheckinStore, Depends(get_journey_checkin_store)],
    notifications: Annotated[NotificationStore, Depends(get_notification_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> JourneyCheckinResponse:
    session, events = store.checkin_journey(cid, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown or ended journey check-in")
    _emit(notifications, cid, events)
    return _journey_checkin_response(session)


@router.post(
    "/journey/checkins/{session_id}/end",
    response_model=JourneyEndResponse,
)
def end_journey_checkin(
    session_id: str,
    payload: JourneyEndRequest,
    request: Request,
    store: Annotated[JourneyCheckinStore, Depends(get_journey_checkin_store)],
    notifications: Annotated[NotificationStore, Depends(get_notification_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> JourneyEndResponse:
    session, events = store.end_journey_checkin(cid, session_id, payload.reason)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown or ended journey check-in")
    _emit(notifications, cid, events)
    if payload.reason == "arrived":
        notifications.record(
            cid,
            "journey_completed",
            {
                "session_id": session.id,
                "ended_at": session.ended_at.isoformat() if session.ended_at else "",
            },
        )
    return JourneyEndResponse(
        session_id=session.id,
        status=session.status,
        ended_at=session.ended_at.isoformat() if session.ended_at else "",
        end_reason=session.end_reason or "",
    )
