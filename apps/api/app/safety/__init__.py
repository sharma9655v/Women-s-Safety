"""Phase 9+ personal safety stores: contacts, sessions, notifications, journey checks, alerts, preferences, discreet mode, fake calls, voice guidance.

Follows the evidence-store pattern (interface + memory + Postgres + registry).
Personal data is keyed by pseudonymous client_id; phone numbers are encrypted
at rest; sessions self-expire on read."""
from __future__ import annotations

from app.safety.alerts import (
    Alert,
    AlertStore,
    MemoryAlertStore,
    PostgresAlertStore,
    get_alert_store,
)
from app.safety.contacts import (
    Contact,
    ContactStore,
    MemoryContactStore,
    PostgresContactStore,
    get_contacts_store,
)
from app.safety.guardian import (
    GuardianSession,
    GuardianStore,
    MemoryGuardianStore,
    PostgresGuardianStore,
    deviation_m,
    get_guardian_store,
)
from app.safety.journey_checkin import (
    JourneyCheckinSession,
    JourneyCheckinStore,
    MemoryJourneyCheckinStore,
    PostgresJourneyCheckinStore,
    get_journey_checkin_store,
)
from app.safety.preferences import (
    SafetyPreferences,
    SafetyPreferencesStore,
    MemorySafetyPreferencesStore,
    PostgresSafetyPreferencesStore,
    get_safety_preferences_store,
)
from app.safety.discreet_mode import (
    DiscreetModeSettings,
    DiscreetModeSettingsStore,
    MemoryDiscreetModeSettingsStore,
    PostgresDiscreetModeSettingsStore,
    get_discreet_mode_settings_store,
)
from app.safety.fake_call import (
    FakeCallSession,
    FakeCallStore,
    MemoryFakeCallStore,
    PostgresFakeCallStore,
    get_fake_call_store,
)
from app.safety.voice_guidance import (
    VoiceGuidanceSession,
    VoiceGuidanceStore,
    MemoryVoiceGuidanceStore,
    PostgresVoiceGuidanceStore,
    get_voice_guidance_store,
)
from app.safety.notifications import (
    MemoryNotificationStore,
    NotificationEvent,
    NotificationStore,
    PostgresNotificationStore,
    get_notification_store,
)
from app.safety.sessions import (
    EmergencySession,
    EmergencyStore,
    MemoryEmergencyStore,
    PostgresEmergencyStore,
    SharingSession,
    get_sessions_store,
)

__all__ = [
    "Contact",
    "ContactStore",
    "EmergencySession",
    "EmergencyStore",
    "Alert",
    "AlertStore",
    "GuardianSession",
    "GuardianStore",
    "MemoryContactStore",
    "MemoryEmergencyStore",
    "MemoryGuardianStore",
    "MemoryAlertStore",
    "MemoryNotificationStore",
    "NotificationEvent",
    "NotificationStore",
    "PostgresContactStore",
    "PostgresEmergencyStore",
    "PostgresGuardianStore",
    "PostgresAlertStore",
    "PostgresNotificationStore",
    "PostgresJourneyCheckinStore",
    "PostgresSafetyPreferencesStore",
    "PostgresDiscreetModeSettingsStore",
    "PostgresFakeCallStore",
    "PostgresVoiceGuidanceStore",
    "SharingSession",
    "JourneyCheckinSession",
    "JourneyCheckinStore",
    "deviation_m",
    "get_alert_store",
    "get_voice_guidance_store",
    "get_contacts_store",
    "get_discreet_mode_settings_store",
    "get_fake_call_store",
    "get_journey_checkin_store",
    "get_notification_store",
    "get_safety_preferences_store",
    "get_sessions_store",
]