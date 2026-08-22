from __future__ import annotations

import math
from dataclasses import dataclass

from app.evidence import SegmentEvidence

# Deterministic baseline knobs. Rule-based per design.md; tuned in Phase 7.
# All functions are pure: same inputs -> same outputs.

INCIDENT_TYPES = ("harassment", "suspicious_activity")
LIGHTING_TYPES = ("streetlight_not_working", "poor_lighting")

# IST hours (UTC + 5:30) considered night: 20:00 - 04:59.
NIGHT_HOURS = (20, 21, 22, 23, 0, 1, 2, 3, 4)
NIGHT_MULTIPLIER = 1.35

# OSM lit tag effect on lighting risk at night.
LIT_TAG_NIGHT_REDUCTION = 0.5
UNLIT_TAG_NIGHT_INCREASE = 1.2

EMERGENCY_FACILITY_TYPES = ("police", "hospital", "fire_station")
FACILITY_NEAR_M = 1000.0
FACILITY_CUTOFF_M = 3000.0
FACILITY_LOGISTIC_CENTER_M = 2000.0
FACILITY_LOGISTIC_SLOPE_M = 600.0

RISK_W_INCIDENT = 0.55
RISK_W_LIGHTING = 0.25
RISK_W_FACILITY = 0.10
RISK_W_ROAD = 0.10

INCIDENT_SCALE = 2.0
LIGHTING_SCALE = 1.5

SPARSE_CONFIDENCE = 0.25
CONFLICT_CONFIDENCE_PENALTY = 0.7
BASE_EVIDENCE_CONFIDENCE = 0.6
EVIDENCE_CONFIDENCE_PER_OBSERVATION = 0.1
CONFIDENCE_CAP = 0.95

REASON_THRESHOLD = 0.05

# Road types with elevated risk at night (no eyes on the street, uneven
# surface). Major carriageways are treated as safer proxies for activity.
ROAD_NIGHT_RISK: dict[str, float] = {
    "footway": 0.25,
    "path": 0.30,
    "pedestrian": 0.20,
    "steps": 0.25,
    "cycleway": 0.20,
    "track": 0.20,
    "service": 0.10,
}


@dataclass(frozen=True)
class SegmentRisk:
    segment_id: int
    risk_probability: float
    confidence: float
    uncertainty: float
    reasons: tuple[str, ...]


def _logistic_facility_risk(distance_m: float) -> float:
    return 1.0 / (
        1.0 + math.exp((FACILITY_LOGISTIC_CENTER_M - distance_m) / FACILITY_LOGISTIC_SLOPE_M)
    )


def compute_segment_risk(
    segment_id: int,
    evidence: SegmentEvidence | None,
    road_type: str | None,
    lit: str | None,
    nearest_emergency_m: float | None,
    hour_ist: int,
) -> SegmentRisk:
    """Deterministic per-segment risk in [0, 1] with confidence in [0, 1].

    Features (design.md): incident count/recency, lighting evidence +
    confidence, emergency-facility distance, road infrastructure, time/day.
    Public transport and activity proxies have no data source yet and are
    intentionally absent (never invented).

    Sparse data -> "Limited safety data" + low confidence.
    """
    is_night = hour_ist in NIGHT_HOURS

    # --- feature contributions -------------------------------------------------
    incident_score = 0.0
    if evidence is not None:
        for obs_type in INCIDENT_TYPES:
            summary = evidence.by_type.get(obs_type)
            if summary is not None:
                incident_score += summary.score
    risk_incident = 1.0 - math.exp(-INCIDENT_SCALE * incident_score)

    lighting_score = 0.0
    streetlight_score = 0.0
    poor_lighting_score = 0.0
    if evidence is not None:
        streetlight = evidence.by_type.get("streetlight_not_working")
        poor = evidence.by_type.get("poor_lighting")
        if streetlight is not None:
            streetlight_score = streetlight.score
        if poor is not None:
            poor_lighting_score = poor.score
        lighting_score = streetlight_score + poor_lighting_score
    risk_lighting = 1.0 - math.exp(-LIGHTING_SCALE * lighting_score)
    if is_night:
        if lit == "yes":
            risk_lighting *= LIT_TAG_NIGHT_REDUCTION
        elif lit == "no":
            risk_lighting *= UNLIT_TAG_NIGHT_INCREASE
    else:
        risk_lighting *= 0.5  # daylight reduces lighting importance

    if nearest_emergency_m is None:
        risk_facility = _logistic_facility_risk(FACILITY_CUTOFF_M)
    else:
        risk_facility = _logistic_facility_risk(nearest_emergency_m)

    risk_road = ROAD_NIGHT_RISK.get(road_type or "", 0.0)
    if risk_road and is_night:
        risk_road *= 1.5
    elif risk_road:
        risk_road *= 0.5

    combined = (
        RISK_W_INCIDENT * risk_incident
        + RISK_W_LIGHTING * min(risk_lighting, 1.0)
        + RISK_W_FACILITY * risk_facility
        + RISK_W_ROAD * risk_road
    )
    if is_night:
        combined *= NIGHT_MULTIPLIER
    risk_probability = max(0.0, min(1.0, combined))

    # --- confidence --------------------------------------------------------------
    has_evidence = evidence is not None and evidence.total_observations > 0
    if evidence is None or evidence.total_observations == 0:
        confidence = SPARSE_CONFIDENCE
    else:
        confidence = BASE_EVIDENCE_CONFIDENCE + EVIDENCE_CONFIDENCE_PER_OBSERVATION * min(
            evidence.total_observations, 4
        )
        if evidence.conflicts:
            confidence *= CONFLICT_CONFIDENCE_PENALTY
    confidence = min(confidence, CONFIDENCE_CAP)
    uncertainty = 1.0 - confidence

    # --- reasons (fixed vocabulary, no invented facts) ---------------------------
    reasons: list[str] = []
    if not has_evidence:
        reasons.append("Limited safety data for this segment")
    else:
        if incident_score > REASON_THRESHOLD:
            reasons.append("Recent incident reports on this segment")
        if streetlight_score > REASON_THRESHOLD:
            reasons.append("Streetlight failure reported on this segment")
        if poor_lighting_score > REASON_THRESHOLD:
            reasons.append("Poor lighting reported on this segment")
        if evidence is not None and evidence.conflicts:
            reasons.append("Conflicting recent evidence on this segment")
    if nearest_emergency_m is not None and nearest_emergency_m < FACILITY_NEAR_M:
        reasons.append("Near an emergency facility")
    elif nearest_emergency_m is None:
        reasons.append(f"No emergency facility within {FACILITY_CUTOFF_M // 1000:.0f} km")
    if is_night and risk_road > 0.0:
        reasons.append("Higher-risk road type for night walking")
    if is_night and lit == "yes" and not reasons:
        reasons.append("Road is tagged as lit (OSM)")

    return SegmentRisk(
        segment_id=segment_id,
        risk_probability=risk_probability,
        confidence=confidence,
        uncertainty=uncertainty,
        reasons=tuple(reasons[:4]),
    )
