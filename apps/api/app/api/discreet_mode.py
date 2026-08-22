"""Discreet safety mode settings (Feature Group S): settings for discreet access
to safety functions without visually obvious emergency screen."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth import require_client_id
from app.identity import client_hash
from app.reports.limiter import RateLimiter, get_rate_limiter
from app.safety import (
    DiscreetModeSettingsStore,
    get_discreet_mode_settings_store,
)
from app.schemas import (
    DiscreetModeSettingsResponse,
    DiscreetModeSettingsUpdate,
)

router = APIRouter(prefix="/api", tags=["discreet_mode"])


def _discreet_limiter() -> RateLimiter:
    return get_rate_limiter("discreet_ratelimit", 20, 60)


def _require_limit(limiter: RateLimiter, cid: str) -> None:
    if not limiter.allow(client_hash(cid)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many discreet mode updates")


@router.get(
    "/discreet-mode",
    response_model=DiscreetModeSettingsResponse,
)
def get_discreet_mode(
    request: Request,
    store: Annotated[DiscreetModeSettingsStore, Depends(get_discreet_mode_settings_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> DiscreetModeSettingsResponse:
    settings = store.get_settings(cid)
    if settings is None:
        from app.schemas import DiscreetModeSettingsResponse as _Resp

        return _Resp(
            client_id=cid,
            enabled=False,
            quick_sos_gesture="triple_tap",
            exit_to_neutral_app=True,
            neutral_app_label="Weather",
            neutral_app_icon="cloud-sun",
        )
    return DiscreetModeSettingsResponse(
        client_id=cid,
        enabled=settings.enabled,
        quick_sos_gesture=settings.quick_sos_gesture,
        exit_to_neutral_app=settings.exit_to_neutral_app,
        neutral_app_label=settings.neutral_app_label,
        neutral_app_icon=settings.neutral_app_icon,
    )


@router.put(
    "/discreet-mode",
    response_model=DiscreetModeSettingsResponse,
)
def update_discreet_mode(
    payload: DiscreetModeSettingsUpdate,
    request: Request,
    store: Annotated[DiscreetModeSettingsStore, Depends(get_discreet_mode_settings_store)],
    limiter: Annotated[RateLimiter, Depends(_discreet_limiter)],
    cid: Annotated[str, Depends(require_client_id)],
) -> DiscreetModeSettingsResponse:
    _require_limit(limiter, cid)
    settings = store.update_settings(
        cid,
        enabled=payload.enabled,
        quick_sos_gesture=payload.quick_sos_gesture,
        exit_to_neutral_app=payload.exit_to_neutral_app,
        neutral_app_label=payload.neutral_app_label,
        neutral_app_icon=payload.neutral_app_icon,
    )
    return DiscreetModeSettingsResponse(
        client_id=cid,
        enabled=settings.enabled,
        quick_sos_gesture=settings.quick_sos_gesture,
        exit_to_neutral_app=settings.exit_to_neutral_app,
        neutral_app_label=settings.neutral_app_label,
        neutral_app_icon=settings.neutral_app_icon,
    )
