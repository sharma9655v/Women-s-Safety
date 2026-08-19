"""Fake call / distraction tool (Feature Group T): user-controlled local utility
for simulated incoming calls."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth import require_client_id
from app.identity import client_hash
from app.reports.limiter import RateLimiter, get_rate_limiter
from app.safety import (
    FakeCallStore,
    get_fake_call_store,
)
from app.schemas import (
    FakeCallCreate,
    FakeCallResponse,
    FakeCallStatusResponse,
)

router = APIRouter(prefix="/api", tags=["fake_call"])


def _fake_call_limiter() -> RateLimiter:
    return get_rate_limiter("fake_call_ratelimit", 10, 60)


def _require_limit(limiter: RateLimiter, cid: str) -> None:
    if not limiter.allow(client_hash(cid)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many fake call actions")


@router.post(
    "/fake-call",
    response_model=FakeCallResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_fake_call(
    payload: FakeCallCreate,
    request: Request,
    store: Annotated[FakeCallStore, Depends(get_fake_call_store)],
    limiter: Annotated[RateLimiter, Depends(_fake_call_limiter)],
    cid: Annotated[str, Depends(require_client_id)],
) -> FakeCallResponse:
    _require_limit(limiter, cid)
    fake_call = store.create_fake_call(
        cid,
        caller_name=payload.caller_name,
        caller_number=payload.caller_number,
        scheduled_at=payload.scheduled_at or datetime.now(UTC),
    )
    return FakeCallResponse(
        id=fake_call.id,
        caller_name=fake_call.caller_name,
        caller_number=fake_call.caller_number,
        scheduled_at=fake_call.scheduled_at.isoformat(),
        status=fake_call.status,
    )


@router.get(
    "/fake-call/status",
    response_model=FakeCallStatusResponse | None,
)
def get_fake_call_status(
    request: Request,
    store: Annotated[FakeCallStore, Depends(get_fake_call_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> FakeCallStatusResponse | None:
    """Latest fake call for this device, or HTTP 200 with a null body when none
    exists (same convention as the other active-session endpoints)."""
    fake_call = store.latest_fake_call(cid)
    if fake_call is None:
        return None
    return FakeCallStatusResponse(
        id=fake_call.id,
        caller_name=fake_call.caller_name,
        caller_number=fake_call.caller_number,
        scheduled_at=fake_call.scheduled_at.isoformat(),
        status=fake_call.status,
    )


@router.get(
    "/fake-call/{call_id}",
    response_model=FakeCallStatusResponse,
)
def get_fake_call_by_id(
    call_id: str,
    request: Request,
    store: Annotated[FakeCallStore, Depends(get_fake_call_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> FakeCallStatusResponse:
    fake_call = store.get_fake_call(cid, call_id)
    if fake_call is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fake call not found")
    return FakeCallStatusResponse(
        id=fake_call.id,
        caller_name=fake_call.caller_name,
        caller_number=fake_call.caller_number,
        scheduled_at=fake_call.scheduled_at.isoformat(),
        status=fake_call.status,
    )
