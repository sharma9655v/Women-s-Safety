"""Device session token endpoints (Group D auth)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth import (
    MemoryDeviceSessionStore,
    PostgresDeviceSessionStore,
    get_device_session_store,
)
from app.config import settings
from app.identity import client_hash, client_id_from_header
from app.reports.limiter import RateLimiter, get_rate_limiter
from app.schemas import (
    DeviceSessionRequest,
    DeviceSessionResponse,
    RevokeSessionResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _auth_limiter() -> RateLimiter:
    return get_rate_limiter("auth_ratelimit", 10, 60)


def _ttl() -> timedelta:
    return timedelta(days=settings.device_session_ttl_days)


@router.post("/device", response_model=DeviceSessionResponse)
def create_device_session(
    payload: DeviceSessionRequest,
    request: Request,
    store: Annotated[
        MemoryDeviceSessionStore | PostgresDeviceSessionStore,
        Depends(get_device_session_store),
    ],
    limiter: Annotated[RateLimiter, Depends(_auth_limiter)],
) -> DeviceSessionResponse:
    """Issue a revocable bearer token bound to the device's client_id."""
    cid = client_id_from_header(payload.client_id)
    if not limiter.allow(client_hash(cid)):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many session requests — try again later",
        )
    token = store.create(cid, _ttl())
    return DeviceSessionResponse(
        token=token,
        client_id=cid,
        expires_at=(datetime.now(UTC) + _ttl()).isoformat(),
    )


@router.post("/revoke", response_model=RevokeSessionResponse)
def revoke_device_session(
    request: Request,
    store: Annotated[
        MemoryDeviceSessionStore | PostgresDeviceSessionStore,
        Depends(get_device_session_store),
    ],
) -> RevokeSessionResponse:
    """Revoke the presented bearer token (device logout)."""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Missing bearer token"
        )
    token = auth[7:].strip()
    store.revoke(token)
    return RevokeSessionResponse(revoked=True)