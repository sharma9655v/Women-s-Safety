from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

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
