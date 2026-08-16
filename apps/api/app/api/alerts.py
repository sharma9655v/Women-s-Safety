"""Safety alerts (Feature Group K): verified safety alerts from the backend.

Categories: recent_verified_incident, lighting_issue, road_hazard,
blocked_sidewalk, route_obstruction, weather_hazard, emergency_event,
public_safety_notice.

Each alert contains: category, location, severity, timestamp, source,
evidence status, freshness, confidence.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.config import settings
from app.auth import require_client_id
from app.identity import client_hash
from app.reports.limiter import RateLimiter, get_rate_limiter
from app.safety import NotificationStore, get_notification_store
from app.safety.alerts import Alert, AlertStore, get_alert_store
from app.schemas import AlertCreate, AlertResponse, AlertListResponse

router = APIRouter(prefix="/api", tags=["safety_alerts"])


def _alerts_limiter() -> RateLimiter:
    return get_rate_limiter("safety_alert_ratelimit", 20, 60)


def _require_limit(limiter: RateLimiter, cid: str) -> None:
    if not limiter.allow(client_hash(cid)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many safety alerts")


def _alert_response(alert: Alert) -> AlertResponse:
    return AlertResponse(
        id=alert.id,
        category=alert.category,
        severity=alert.severity,
        lat=alert.lat,
        lon=alert.lon,
        location_name=alert.location_name,
        description=alert.description,
        source=alert.source,
        evidence_status=alert.evidence_status,
        confidence=alert.confidence,
        observed_at=alert.observed_at.isoformat(),
        expires_at=alert.expires_at.isoformat() if alert.expires_at else None,
        created_at=alert.created_at.isoformat(),
    )


@router.post(
    "/alerts",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_alert(
    payload: AlertCreate,
    request: Request,
    store: Annotated[AlertStore, Depends(get_alert_store)],
    notifications: Annotated[NotificationStore, Depends(get_notification_store)],
    limiter: Annotated[RateLimiter, Depends(_alerts_limiter)],
    cid: Annotated[str, Depends(require_client_id)],
) -> AlertResponse:
    _require_limit(limiter, cid)
    alert = store.create_alert(
        cid,
        category=payload.category,
        severity=payload.severity,
        lat=payload.lat,
        lon=payload.lon,
        location_name=payload.location_name,
        description=payload.description,
        source=payload.source,
    )
    notifications.record(
        cid,
        "safety_alert",
        {"alert_id": alert.id, "category": alert.category, "severity": alert.severity},
    )
    return _alert_response(alert)


@router.get(
    "/alerts",
    response_model=AlertListResponse,
)
def list_alerts(
    request: Request,
    store: Annotated[AlertStore, Depends(get_alert_store)],
    cid: Annotated[str, Depends(require_client_id)],
    limit: int = Query(default=50, ge=1, le=200),
) -> AlertListResponse:
    alerts = store.list_alerts(cid, limit)
    return AlertListResponse(alerts=[_alert_response(a) for a in alerts])


@router.get(
    "/alerts/active",
    response_model=AlertListResponse,
)
def active_alerts(
    request: Request,
    store: Annotated[AlertStore, Depends(get_alert_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> AlertListResponse:
    alerts = store.active_alerts(cid)
    return AlertListResponse(alerts=[_alert_response(a) for a in alerts])