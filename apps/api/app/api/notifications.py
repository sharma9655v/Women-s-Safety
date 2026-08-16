"""In-app notification events (Phase 9). The notification center reads only
the owning client's events. Delivery status is honest: 'no_channel' when no
provider is configured, 'queued' when one is."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.auth import require_client_id
from app.safety import NotificationStore, get_notification_store
from app.schemas import NotificationEventResponse, NotificationListResponse
from app.safety.journey_checkin import JourneyCheckinSession

router = APIRouter(prefix="/api", tags=["notifications"])


@router.get("/notifications", response_model=NotificationListResponse)
def list_notifications(
    request: Request,
    store: Annotated[NotificationStore, Depends(get_notification_store)],
    cid: Annotated[str, Depends(require_client_id)],
    limit: int = Query(default=50, ge=1, le=200),
) -> NotificationListResponse:
    events = store.recent(cid, limit)
    return NotificationListResponse(
        notifications=[
            NotificationEventResponse(
                id=e.id,
                type=e.type,
                channel=e.channel,
                status=e.status,
                payload=e.payload,
                created_at=e.created_at.isoformat(),
            )
            for e in events
        ]
    )
