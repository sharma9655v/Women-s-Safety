"""Personal safety preferences (Feature Group Q): user-configurable route preferences
that influence routing but never bypass the core safety model.

Stored per client, returned via /api/preferences endpoint."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import settings
from app.auth import require_client_id
from app.identity import client_hash
from app.reports.limiter import RateLimiter, get_rate_limiter
from app.safety import (
    SafetyPreferences,
    SafetyPreferencesStore,
    get_safety_preferences_store,
)
from app.schemas import (
    SafetyPreferencesResponse,
    SafetyPreferencesUpdate,
)

router = APIRouter(prefix="/api", tags=["safety_preferences"])


def _preferences_limiter() -> RateLimiter:
    return get_rate_limiter("preference_ratelimit", 20, 60)


def _require_limit(limiter: RateLimiter, cid: str) -> None:
    if not limiter.allow(client_hash(cid)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many preference updates")


@router.get(
    "/preferences",
    response_model=SafetyPreferencesResponse,
)
def get_preferences(
    request: Request,
    store: Annotated[SafetyPreferencesStore, Depends(get_safety_preferences_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> SafetyPreferencesResponse:
    prefs = store.get_preferences(cid)
    if prefs is None:
        # Return defaults
        from app.schemas import SafetyPreferencesResponse as _Resp
        return _Resp(
            client_id=cid,
            prefer_better_lit=True,
            prefer_main_roads=True,
            prefer_near_emergency=True,
            avoid_known_hazards=True,
            avoid_isolated_roads=False,
            minimize_walking_time=False,
            default_profile="balanced",
            discreet_mode_enabled=False,
            voice_guidance_enabled=True,
            voice_language="en",
        )
    return SafetyPreferencesResponse(
        client_id=cid,
        prefer_better_lit=prefs.prefer_better_lit,
        prefer_main_roads=prefs.prefer_main_roads,
        prefer_near_emergency=prefs.prefer_near_emergency,
        avoid_known_hazards=prefs.avoid_known_hazards,
        avoid_isolated_roads=prefs.avoid_isolated_roads,
        minimize_walking_time=prefs.minimize_walking_time,
        default_profile=prefs.default_profile,
        discreet_mode_enabled=prefs.discreet_mode_enabled,
        voice_guidance_enabled=prefs.voice_guidance_enabled,
        voice_language=prefs.voice_language,
    )


@router.put(
    "/preferences",
    response_model=SafetyPreferencesResponse,
)
def update_preferences(
    payload: SafetyPreferencesUpdate,
    request: Request,
    store: Annotated[SafetyPreferencesStore, Depends(get_safety_preferences_store)],
    limiter: Annotated[RateLimiter, Depends(_preferences_limiter)],
    cid: Annotated[str, Depends(require_client_id)],
) -> SafetyPreferencesResponse:
    _require_limit(limiter, cid)
    prefs = store.update_preferences(
        cid,
        prefer_better_lit=payload.prefer_better_lit,
        prefer_main_roads=payload.prefer_main_roads,
        prefer_near_emergency=payload.prefer_near_emergency,
        avoid_known_hazards=payload.avoid_known_hazards,
        avoid_isolated_roads=payload.avoid_isolated_roads,
        minimize_walking_time=payload.minimize_walking_time,
        default_profile=payload.default_profile,
        discreet_mode_enabled=payload.discreet_mode_enabled,
        voice_guidance_enabled=payload.voice_guidance_enabled,
        voice_language=payload.voice_language,
    )
    return SafetyPreferencesResponse(
        client_id=cid,
        prefer_better_lit=prefs.prefer_better_lit,
        prefer_main_roads=prefs.prefer_main_roads,
        prefer_near_emergency=prefs.prefer_near_emergency,
        avoid_known_hazards=prefs.avoid_known_hazards,
        avoid_isolated_roads=prefs.avoid_isolated_roads,
        minimize_walking_time=prefs.minimize_walking_time,
        default_profile=prefs.default_profile,
        discreet_mode_enabled=prefs.discreet_mode_enabled,
        voice_guidance_enabled=prefs.voice_guidance_enabled,
        voice_language=prefs.voice_language,
    )