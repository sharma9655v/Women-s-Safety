from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

RouteMode = Literal["walking", "driving", "cycling"]
SafetyPreference = Literal["safety", "balanced", "time"]
RouteType = Literal["safety_priority", "balanced", "time_priority"]


class LatLon(BaseModel):
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)


class RouteRequest(BaseModel):
    origin: LatLon
    destination: LatLon
    mode: RouteMode = "walking"
    safety_preference: SafetyPreference = "balanced"
    hour_ist: int | None = Field(
        default=None,
        ge=0,
        le=23,
        description="Optional simulated IST hour (demo use only; the UI labels it as such).",
    )


class RouteGeometry(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: list[tuple[float, float]]


class RouteCandidate(BaseModel):
    index: int = Field(ge=0)
    distance_m: float = Field(ge=0)
    duration_s: float = Field(ge=0)
    geometry: RouteGeometry
    warnings: list[str] = Field(default_factory=list)
    segment_ids: list[int] = Field(default_factory=list)


class RouteResult(BaseModel):
    """One of the three ranked route types.

    estimated_safety is an estimate, never a guarantee: the response has no
    boolean "safe" field by design (api-spec.md).
    """

    route_type: RouteType
    distance_m: float = Field(ge=0)
    duration_s: float = Field(ge=0)
    risk_probability: float = Field(ge=0, le=1)
    estimated_safety: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    uncertainty: float = Field(ge=0, le=1)
    high_risk_fraction: float = Field(
        default=0.0, ge=0, le=1, description="Length-weighted share of the route at risk >= 0.5"
    )
    risk_exposure_m: float = Field(
        default=0.0,
        ge=0,
        description="Length-weighted risk exposure: effective risky metres (sum length x risk)",
    )
    warnings: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    model_version: str
    segment_ids: list[int] = Field(default_factory=list)
    geometry: RouteGeometry


class RoutesResponse(BaseModel):
    routes: list[RouteResult]


class EvidenceTypeSummary(BaseModel):
    observation_type: str
    count: int
    score: float
    freshness: float
    confidence: float
    conflicts: bool
    source_counts: dict[str, int]
    state_counts: dict[str, int]
    distinct_source_types: int = 0
    corroborated: bool = False


class SegmentEvidenceResponse(BaseModel):
    """Per-segment evidence summary.

    Privacy contract: aggregate counts and scores only — never reporter
    identity and never report descriptions.
    """

    segment_id: int
    total_observations: int
    overall_freshness: float
    overall_confidence: float
    conflicts: list[str]
    by_type: dict[str, EvidenceTypeSummary]
    model_version: str


ReportCategory = Literal[
    "streetlight_not_working",
    "poor_lighting",
    "harassment",
    "suspicious_activity",
    "blocked_sidewalk",
    "unsafe_transport",
    "road_hazard",
    "other",
]


class ReportRequest(BaseModel):
    """Anonymous report. No identity fields are accepted by design.

    description and evidence_image (base64, optional) are redacted/stripped
    server-side and are never returned by any API.
    """

    segment_id: int = Field(ge=0)
    category: ReportCategory
    description: str | None = Field(default=None, max_length=500)
    evidence_image: str | None = Field(default=None, max_length=5_000_000)


class ReportResponse(BaseModel):
    """Confirmation of an accepted report — content-free by design."""

    report_id: int
    segment_id: int
    category: ReportCategory
    verification_state: str
    model_version: str


class QuickReportRequest(BaseModel):
    """Minimal report for fast submission in time-sensitive situations.

    Only category is required. Description and segment_id are optional —
    the API will use the current location if segment_id is not provided.
    """

    category: ReportCategory
    segment_id: int | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=100)


class QuickReportResponse(BaseModel):
    """Confirmation of a quick anonymous report."""

    report_id: int
    segment_id: int
    category: ReportCategory
    verification_state: str


class RecomputeRequest(BaseModel):
    segment_id: int | None = None


class RecomputeResponse(BaseModel):
    recomputed: int
    segments: int


class MlGate(BaseModel):
    """ML training gate (thresholds mirror ml/ml/gate.py)."""

    open: bool
    verified_observations: int = Field(ge=0)
    span_days: float | None = Field(default=None, ge=0)
    min_verified_observations: int = Field(default=1_000)
    min_span_days: int = Field(default=90)


class ModelsCurrentResponse(BaseModel):
    """Active model versions + dataset audit trail (api-spec:
    GET /api/models/current)."""

    risk_model: str
    evidence_model: str
    dataset_versions: list[str]
    ml_gate: MlGate


class AdminReport(BaseModel):
    """One report row for admin review. Privacy contract: no description,
    no image, no client hash — identity and content never leave the API."""

    report_id: int
    segment_id: int
    category: str
    verification_state: str
    reported_at: str
    confidence: float


class AdminReportListResponse(BaseModel):
    reports: list[AdminReport]


class AdminVerificationResponse(BaseModel):
    report_id: int
    verification_state: str


class GeocodeResult(BaseModel):
    name: str
    kind: Literal["area", "facility"]
    type: str | None = None
    lat: float
    lon: float


class GeocodeResponse(BaseModel):
    results: list[GeocodeResult]


# --- Phase 9: personal safety (contacts / emergency / sharing / notifications)


class TrustedContact(BaseModel):
    """A trusted contact. The phone number is returned only to the owning
    client and is encrypted at rest."""

    id: int
    name: str
    relationship: str
    phone: str
    role: Literal["primary", "secondary"]
    enabled: bool


class TrustedContactListResponse(BaseModel):
    contacts: list[TrustedContact]


class TrustedContactInput(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    relationship: str = Field(default="friend", min_length=1, max_length=30)
    phone: str = Field(min_length=7, max_length=20)
    role: Literal["primary", "secondary"] = "secondary"


class TrustedContactUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    relationship: str | None = Field(default=None, min_length=1, max_length=30)
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    role: Literal["primary", "secondary"] | None = None
    enabled: bool | None = None


class EmergencyCreateRequest(BaseModel):
    """Sent only after the client-side countdown completes (a cancel never
    reaches the backend). Location is the last known position."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    notified_contact_ids: list[int] = Field(default_factory=list, max_length=20)


class EmergencySessionResponse(BaseModel):
    session_id: str
    status: str
    started_at: str
    ended_at: str | None
    end_reason: str | None
    latitude: float | None
    longitude: float | None
    last_known_at: str | None
    notified_contact_ids: list[int]
    notify_status: str
    location_sharing: str | None


class EmergencyEndRequest(BaseModel):
    reason: str = Field(default="ended_by_user", max_length=50)


class EmergencyEndResponse(BaseModel):
    session_id: str
    status: str
    ended_at: str
    end_reason: str


class SharingStartRequest(BaseModel):
    kind: Literal["EMERGENCY", "GUARDIAN"] = "EMERGENCY"
    owner_session: str | None = None
    ttl_s: int = Field(default=1800, ge=60, le=86400)
    recipient_ids: list[int] = Field(default_factory=list, max_length=20)


class SharingSessionResponse(BaseModel):
    session_id: str
    kind: str
    status: str
    started_at: str
    expires_at: str
    stopped_at: str | None
    latitude: float | None
    longitude: float | None
    last_updated_at: str | None
    recipient_ids: list[int]


class SharingLocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class NotificationEventResponse(BaseModel):
    id: int
    type: str
    channel: str
    status: str
    payload: dict[str, object]
    created_at: str


class NotificationListResponse(BaseModel):
    notifications: list[NotificationEventResponse]


# --- Phase 10: guardian journeys (check-ins, escalation, deviation)


class GuardianCreateRequest(BaseModel):
    """Start a guardian journey. Geometry is the planned route the owner
    chose (used only to detect deviation), never invented data."""

    guardian_contact_ids: list[int] = Field(default_factory=list, max_length=20)
    expected_arrival_at: datetime | None = None
    planned_geometry: list[list[float]] | None = Field(default=None, max_length=20000)
    checkin_grace_s: int = Field(default=300, ge=60, le=7200)

    @field_validator("planned_geometry")
    @classmethod
    def _valid_geometry(cls, geometry: list[list[float]] | None) -> list[list[float]] | None:
        if geometry is None:
            return None
        for point in geometry:
            if len(point) != 2:
                raise ValueError("each geometry point must be [lon, lat]")
            lon, lat = point
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                raise ValueError("geometry coordinates out of bounds")
        if len(geometry) == 1:
            raise ValueError("geometry needs at least 2 points")
        return geometry


class GuardianSessionResponse(BaseModel):
    session_id: str
    status: str
    started_at: str
    ended_at: str | None
    end_reason: str | None
    guardian_contact_ids: list[int]
    expected_arrival_at: str | None
    checkin_deadline: str
    checkin_grace_s: int
    last_checkin_at: str | None
    latitude: float | None
    longitude: float | None
    last_known_at: str | None
    deviation_detected: bool
    first_deviation_at: str | None
    escalation_stage: int


class GuardianEndRequest(BaseModel):
    reason: Literal["arrived", "cancelled"] = "cancelled"


class GuardianEndResponse(BaseModel):
    session_id: str
    status: str
    ended_at: str
    end_reason: str


class JourneyCheckinCreate(BaseModel):
    destination_name: str
    destination_lat: float = Field(ge=-90, le=90)
    destination_lon: float = Field(ge=-180, le=180)
    expected_arrival_at: datetime | None = None
    checkin_interval_s: int = Field(default=900, ge=60, le=3600)
    checkin_grace_s: int = Field(default=300, ge=60, le=7200)
    contact_ids: list[int] = Field(default_factory=list, max_length=20)


class JourneyCheckinResponse(BaseModel):
    session_id: str
    status: str
    started_at: str
    ended_at: str | None
    end_reason: str | None
    destination_name: str
    destination_lat: float | None
    destination_lon: float | None
    expected_arrival_at: str | None
    checkin_interval_s: int
    checkin_grace_s: int
    last_checkin_at: str | None
    next_checkin_at: str | None
    contact_ids: list[int]
    escalation_stage: int
    notified_stage: int
    latitude: float | None
    longitude: float | None
    last_known_at: str | None


class JourneyEndRequest(BaseModel):
    reason: Literal["arrived", "cancelled"] = "arrived"


class JourneyEndResponse(BaseModel):
    session_id: str
    status: str
    ended_at: str
    end_reason: str


class AlertCreate(BaseModel):
    category: str = Field(
        ...,
        pattern="^(recent_verified_incident|lighting_issue|road_hazard|blocked_sidewalk|route_obstruction|weather_hazard|emergency_event|public_safety_notice)$",
    )
    severity: str = Field(default="moderate", pattern="^(low|moderate|high|critical)$")
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    location_name: str | None = None
    description: str | None = None
    source: str = "community"


class AlertResponse(BaseModel):
    id: int
    category: str
    severity: str
    lat: float
    lon: float
    location_name: str | None
    description: str | None
    source: str
    evidence_status: str
    confidence: float
    observed_at: str
    expires_at: str | None
    created_at: str


class AlertListResponse(BaseModel):
    alerts: list[AlertResponse]


class SafetyPreferencesResponse(BaseModel):
    client_id: str
    prefer_better_lit: bool
    prefer_main_roads: bool
    prefer_near_emergency: bool
    avoid_known_hazards: bool
    avoid_isolated_roads: bool
    minimize_walking_time: bool
    default_profile: str
    discreet_mode_enabled: bool
    voice_guidance_enabled: bool
    voice_language: str


class SafetyPreferencesUpdate(BaseModel):
    prefer_better_lit: bool
    prefer_main_roads: bool
    prefer_near_emergency: bool
    avoid_known_hazards: bool
    avoid_isolated_roads: bool
    minimize_walking_time: bool
    default_profile: str
    discreet_mode_enabled: bool
    voice_guidance_enabled: bool
    voice_language: str


class DiscreetModeSettingsResponse(BaseModel):
    client_id: str
    enabled: bool
    quick_sos_gesture: str
    exit_to_neutral_app: bool
    neutral_app_label: str
    neutral_app_icon: str


class DiscreetModeSettingsUpdate(BaseModel):
    enabled: bool
    quick_sos_gesture: str
    exit_to_neutral_app: bool
    neutral_app_label: str
    neutral_app_icon: str


class FakeCallCreate(BaseModel):
    caller_name: str = Field(min_length=1, max_length=60)
    caller_number: str | None = Field(default=None, max_length=20)
    scheduled_at: datetime | None = Field(
        default=None,
        description="Optional scheduled ring time; defaults to now when omitted.",
    )


class FakeCallResponse(BaseModel):
    id: str
    caller_name: str
    caller_number: str | None
    scheduled_at: str
    status: str


class FakeCallStatusResponse(BaseModel):
    id: str
    caller_name: str
    caller_number: str | None
    scheduled_at: str
    status: str


class VoiceGuidanceStart(BaseModel):
    route_session_id: str | None = None
    language: str = "en"


class VoiceGuidanceResponse(BaseModel):
    session_id: str
    client_id: str
    route_session_id: str | None
    language: str
    active: bool
    started_at: str
    ended_at: str | None


class VoiceGuidanceStatusResponse(BaseModel):
    session_id: str
    client_id: str
    route_session_id: str | None
    language: str
    active: bool
    started_at: str
    ended_at: str | None


class CommunityCreateRequest(BaseModel):
    """Submit an anonymous community update. Posts start PENDING and are
    moderated before they read as verified."""

    kind: Literal["alert", "route_update", "photo"]
    location: str = Field(min_length=2, max_length=60)
    text: str = Field(min_length=10, max_length=280)


class CommunityPostResponse(BaseModel):
    """Public feed item. client_id is never exposed."""

    id: str
    kind: str
    location: str
    text: str
    status: str
    created_at: str


class CommunityFeedResponse(BaseModel):
    posts: list[CommunityPostResponse]


class CommunityModerateResponse(BaseModel):
    id: str
    status: Literal["VERIFIED", "REJECTED"]


class PrivacyDashboardResponse(BaseModel):
    """Privacy center summary. Honest by design: report history is anonymous
    and cannot be listed per device, so it is not claimed here."""

    location_sharing_active: bool
    location_sharing_expires_at: str | None = None
    guardian_active: bool
    guardian_checkin_deadline: str | None = None
    trusted_contact_count: int
    emergency_active: bool
    emergency_notify_status: str | None = None
    voice_guidance_active: bool
    voice_language: str
    discreet_mode_enabled: bool


class PrivacySettingsResponse(BaseModel):
    """Settings the Privacy Center can change (persisted per client)."""

    voice_guidance_enabled: bool
    voice_language: str
    discreet_mode_enabled: bool


class PrivacySettingsUpdate(BaseModel):
    """Partial update of privacy-center settings."""

    voice_guidance_enabled: bool | None = None
    voice_language: str | None = Field(default=None, pattern="^(en|hi)$", description="en or hi")
    discreet_mode_enabled: bool | None = None


class DeviceSessionRequest(BaseModel):
    client_id: str


class DeviceSessionResponse(BaseModel):
    token: str
    client_id: str
    expires_at: str


class RevokeSessionResponse(BaseModel):
    revoked: bool
