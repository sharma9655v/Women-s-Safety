"""Voice safety assistance (Feature Group U): voice guidance settings and session
tracking for navigation voice prompts."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import settings
from app.auth import require_client_id
from app.identity import client_hash
from app.reports.limiter import RateLimiter, get_rate_limiter
from app.safety import (
    VoiceGuidanceSession,
    VoiceGuidanceStore,
    get_voice_guidance_store,
)
from app.schemas import (
    VoiceGuidanceStart,
    VoiceGuidanceResponse,
    VoiceGuidanceStatusResponse,
)

router = APIRouter(prefix="/api", tags=["voice_guidance"])


def _voice_limiter() -> RateLimiter:
    return get_rate_limiter("voice_ratelimit", 20, 60)


def _require_limit(limiter: RateLimiter, cid: str) -> None:
    if not limiter.allow(client_hash(cid)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many voice guidance actions")


@router.post(
    "/voice/start",
    response_model=VoiceGuidanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_voice_guidance(
    payload: VoiceGuidanceStart,
    request: Request,
    store: Annotated[VoiceGuidanceStore, Depends(get_voice_guidance_store)],
    limiter: Annotated[RateLimiter, Depends(_voice_limiter)],
    cid: Annotated[str, Depends(require_client_id)],
) -> VoiceGuidanceResponse:
    _require_limit(limiter, cid)
    session = store.start_voice_guidance(
        cid,
        route_session_id=payload.route_session_id,
        language=payload.language,
    )
    return VoiceGuidanceResponse(
        session_id=session.id,
        client_id=cid,
        route_session_id=session.route_session_id,
        language=session.language,
        active=session.active,
        started_at=session.started_at.isoformat(),
        ended_at=None,
    )


@router.post(
    "/voice/stop",
    response_model=VoiceGuidanceResponse,
)
def stop_voice_guidance(
    request: Request,
    store: Annotated[VoiceGuidanceStore, Depends(get_voice_guidance_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> VoiceGuidanceResponse:
    session = store.stop_voice_guidance(cid)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Voice guidance session not found")
    return VoiceGuidanceResponse(
        session_id=session.id,
        client_id=cid,
        route_session_id=session.route_session_id,
        language=session.language,
        active=session.active,
        started_at=session.started_at.isoformat(),
        ended_at=session.ended_at.isoformat() if session.ended_at else "",
    )


@router.get(
    "/voice/status",
    response_model=VoiceGuidanceStatusResponse,
)
def get_voice_status(
    request: Request,
    store: Annotated[VoiceGuidanceStore, Depends(get_voice_guidance_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> VoiceGuidanceStatusResponse:
    session = store.get_voice_status(cid)
    if session is None:
        from app.schemas import VoiceGuidanceStatusResponse as _Resp
        return _Resp(
            session_id="",
            client_id=cid,
            route_session_id=None,
            language="en",
            active=False,
            started_at="",
            ended_at="",
        )
    return VoiceGuidanceStatusResponse(
        session_id=session.id,
        client_id=cid,
        route_session_id=session.route_session_id,
        language=session.language,
        active=session.active,
        started_at=session.started_at.isoformat(),
        ended_at=session.ended_at.isoformat() if session.ended_at else "",
    )