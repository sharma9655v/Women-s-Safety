"""Privacy center (Feature Group X): dashboard and settings for personal data.

Shows location sharing, guardian mode, trusted contacts, emergency sessions,
voice guidance and discreet mode. All personal data is keyed by the
pseudonymous client_id; anonymous reports are NOT listed because they are not
linkable to a device by design (that would break the anonymity contract)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth import require_client_id
from app.identity import client_hash
from app.reports.limiter import RateLimiter, get_rate_limiter
from app.safety import (
    ContactStore,
    DiscreetModeSettingsStore,
    EmergencyStore,
    GuardianStore,
    SafetyPreferencesStore,
    VoiceGuidanceStore,
    get_contacts_store,
    get_discreet_mode_settings_store,
    get_guardian_store,
    get_safety_preferences_store,
    get_sessions_store,
    get_voice_guidance_store,
)
from app.schemas import (
    PrivacyDashboardResponse,
    PrivacySettingsResponse,
    PrivacySettingsUpdate,
)

router = APIRouter(prefix="/api", tags=["privacy"])

_DEFAULT_PREFS = {
    "prefer_better_lit": True,
    "prefer_main_roads": True,
    "prefer_near_emergency": True,
    "avoid_known_hazards": True,
    "avoid_isolated_roads": False,
    "minimize_walking_time": False,
    "default_profile": "balanced",
    "discreet_mode_enabled": False,
    "voice_guidance_enabled": True,
    "voice_language": "en",
}


def _privacy_limiter() -> RateLimiter:
    return get_rate_limiter("privacy_ratelimit", 20, 60)


def _require_limit(limiter: RateLimiter, cid: str) -> None:
    if not limiter.allow(client_hash(cid)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many privacy actions")


def _settings_response(
    prefs: SafetyPreferencesStore,
    discreet: DiscreetModeSettingsStore,
    cid: str,
) -> PrivacySettingsResponse:
    preferences = prefs.get_preferences(cid)
    discreet_settings = discreet.get_settings(cid)
    if preferences is not None:
        return PrivacySettingsResponse(
            voice_guidance_enabled=preferences.voice_guidance_enabled,
            voice_language=preferences.voice_language,
            discreet_mode_enabled=preferences.discreet_mode_enabled,
        )
    return PrivacySettingsResponse(
        voice_guidance_enabled=True,
        voice_language="en",
        discreet_mode_enabled=discreet_settings.enabled if discreet_settings else False,
    )


@router.get("/privacy/dashboard", response_model=PrivacyDashboardResponse)
def privacy_dashboard(
    request: Request,
    contacts: Annotated[ContactStore, Depends(get_contacts_store)],
    sessions: Annotated[EmergencyStore, Depends(get_sessions_store)],
    guardian: Annotated[GuardianStore, Depends(get_guardian_store)],
    voice: Annotated[VoiceGuidanceStore, Depends(get_voice_guidance_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> PrivacyDashboardResponse:
    """Return the privacy dashboard state for the current client."""
    sharing = sessions.active_sharing(cid)
    emergency = sessions.active_emergency(cid)
    guardian_session, _events = guardian.active_guardian(cid)
    voice_status = voice.get_voice_status(cid)
    contact_list = contacts.list(cid)
    preferences = get_safety_preferences_store().get_preferences(cid)
    return PrivacyDashboardResponse(
        location_sharing_active=sharing is not None,
        location_sharing_expires_at=(
            sharing.expires_at.isoformat() if sharing is not None else None
        ),
        guardian_active=guardian_session is not None,
        guardian_checkin_deadline=(
            guardian_session.checkin_deadline.isoformat() if guardian_session is not None else None
        ),
        trusted_contact_count=len(contact_list),
        emergency_active=emergency is not None,
        emergency_notify_status=emergency.notify_status if emergency is not None else None,
        voice_guidance_active=bool(voice_status and voice_status.active),
        voice_language=voice_status.language if voice_status else "en",
        discreet_mode_enabled=bool(preferences and preferences.discreet_mode_enabled),
    )


@router.get("/privacy/settings", response_model=PrivacySettingsResponse)
def get_privacy_settings(
    request: Request,
    prefs: Annotated[SafetyPreferencesStore, Depends(get_safety_preferences_store)],
    discreet: Annotated[DiscreetModeSettingsStore, Depends(get_discreet_mode_settings_store)],
    cid: Annotated[str, Depends(require_client_id)],
) -> PrivacySettingsResponse:
    return _settings_response(prefs, discreet, cid)


@router.put("/privacy/settings", response_model=PrivacySettingsResponse)
def update_privacy_settings(
    payload: PrivacySettingsUpdate,
    request: Request,
    prefs: Annotated[SafetyPreferencesStore, Depends(get_safety_preferences_store)],
    discreet: Annotated[DiscreetModeSettingsStore, Depends(get_discreet_mode_settings_store)],
    limiter: Annotated[RateLimiter, Depends(_privacy_limiter)],
    cid: Annotated[str, Depends(require_client_id)],
) -> PrivacySettingsResponse:
    _require_limit(limiter, cid)
    current = prefs.get_preferences(cid)
    if current is not None:
        prefs.update_preferences(
            cid,
            prefer_better_lit=current.prefer_better_lit,
            prefer_main_roads=current.prefer_main_roads,
            prefer_near_emergency=current.prefer_near_emergency,
            avoid_known_hazards=current.avoid_known_hazards,
            avoid_isolated_roads=current.avoid_isolated_roads,
            minimize_walking_time=current.minimize_walking_time,
            default_profile=current.default_profile,
            discreet_mode_enabled=(
                payload.discreet_mode_enabled
                if payload.discreet_mode_enabled is not None
                else current.discreet_mode_enabled
            ),
            voice_guidance_enabled=(
                payload.voice_guidance_enabled
                if payload.voice_guidance_enabled is not None
                else current.voice_guidance_enabled
            ),
            voice_language=payload.voice_language or current.voice_language,
        )
        prefs.update_preferences(
            cid,
            prefer_better_lit=True,
            prefer_main_roads=True,
            prefer_near_emergency=True,
            avoid_known_hazards=True,
            avoid_isolated_roads=False,
            minimize_walking_time=False,
            default_profile="balanced",
            discreet_mode_enabled=bool(payload.discreet_mode_enabled),
            voice_guidance_enabled=bool(payload.voice_guidance_enabled),
            voice_language=payload.voice_language or "en",
        )
    current_settings = discreet.get_settings(cid)
    if current_settings is not None:
        discreet.update_settings(
            cid,
            enabled=(
                payload.discreet_mode_enabled
                if payload.discreet_mode_enabled is not None
                else current_settings.enabled
            ),
            quick_sos_gesture=current_settings.quick_sos_gesture,
            exit_to_neutral_app=current_settings.exit_to_neutral_app,
            neutral_app_label=current_settings.neutral_app_label,
            neutral_app_icon=current_settings.neutral_app_icon,
        )
    elif payload.discreet_mode_enabled is not None:
        discreet.update_settings(
            cid,
            enabled=payload.discreet_mode_enabled,
            quick_sos_gesture="triple_tap",
            exit_to_neutral_app=True,
            neutral_app_label="Weather",
            neutral_app_icon="cloud-sun",
        )
    return _settings_response(prefs, discreet, cid)
