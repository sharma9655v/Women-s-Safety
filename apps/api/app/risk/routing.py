from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from app.facilities.store import Facility
from app.risk.model import SegmentRisk

MODEL_VERSION = "deterministic-baseline-v1"

# Profile weights for  C = a*distance + b*time + g*risk + d*uncertainty,
# where time/risk/uncertainty are converted to distance-equivalents so the
# terms are comparable (design.md routing section).
PROFILES: dict[str, tuple[float, float, float, float]] = {
    "safety_priority": (0.6, 1.0, 2.0, 1.5),
    "balanced": (1.0, 1.0, 1.0, 0.8),
    "time_priority": (0.8, 2.0, 0.3, 0.2),
}
PROFILE_ORDER = ("safety_priority", "balanced", "time_priority")

WALKING_SPEED_MPS = 1.4
# One unit of risk weighs as 4 km of walking, so the safety profile (gamma=2.0)
# strongly avoids risky segments while the time profile (gamma=0.3) tolerates
# them; uncertainty is a milder penalty (400 m per unit).
RISK_DISTANCE_EQUIV_M = 4000.0
UNCERTAINTY_DISTANCE_EQUIV_M = 400.0

SPARSE_WARNING_FRACTION = 0.5
SPARSE_WARNING = "Limited safety data along parts of this route"
CONFLICT_WARNING = "Conflicting recent evidence on parts of this route"

# Segments at or above this risk probability count as a high-risk stretch.
HIGH_RISK_THRESHOLD = 0.5

_EARTH_RADIUS_M = 6371000.0


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2.0 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


def segment_length_m(coords: tuple[tuple[float, float], ...]) -> float:
    return sum(
        haversine_m(prev[0], prev[1], nxt[0], nxt[1])
        for prev, nxt in zip(coords, coords[1:], strict=False)
    )


def nearest_emergency_m(
    lon: float,
    lat: float,
    facilities: Sequence[Facility],
) -> float | None:
    """Haversine distance to the nearest facility (already filtered to
    emergency types by the caller), or None when none are nearby."""
    best: float | None = None
    for facility in facilities:
        distance = haversine_m(lon, lat, facility.lon, facility.lat)
        if best is None or distance < best:
            best = distance
    return best


@dataclass(frozen=True)
class ScoredRoute:
    candidate_index: int
    distance_m: float
    duration_s: float
    segment_lengths: tuple[float, ...]
    segment_risks: tuple[SegmentRisk, ...]
    risk_probability: float
    confidence: float
    uncertainty: float
    sparse_fraction: float
    high_risk_fraction: float
    risk_exposure_m: float
    conflicts_present: bool
    reasons: tuple[str, ...]


def score_candidate(
    candidate_index: int,
    distance_m: float,
    duration_s: float,
    segment_lengths: list[float],
    segment_risks: list[SegmentRisk],
) -> ScoredRoute:
    """Length-weighted route aggregates. Pure and deterministic."""
    total_length = sum(segment_lengths)
    if total_length <= 0.0:
        total_length = len(segment_risks) or 1.0
        weights = [1.0 / total_length] * len(segment_risks)
    else:
        weights = [length / total_length for length in segment_lengths]

    risk = sum(w * r.risk_probability for w, r in zip(weights, segment_risks, strict=True))
    uncertainty = sum(w * r.uncertainty for w, r in zip(weights, segment_risks, strict=True))
    sparse_fraction = sum(
        w for w, r in zip(weights, segment_risks, strict=True) if r.confidence <= 0.3
    )
    high_risk_fraction = sum(
        w
        for w, r in zip(weights, segment_risks, strict=True)
        if r.risk_probability >= HIGH_RISK_THRESHOLD
    )
    # Length-weighted risk exposure: effective "risky metres" on the route
    # (sum of length x risk over segments). Zero when no segment lengths are
    # known — honest rather than invented. Non-strict zip: lengths may be
    # shorter than risks when segment geometries are missing.
    risk_exposure_m = sum(
        length * r.risk_probability
        for length, r in zip(segment_lengths, segment_risks, strict=False)
    )

    reasons_counter: Counter[str] = Counter()
    for r in segment_risks:
        reasons_counter.update(r.reasons)
    reasons = tuple(reason for reason, _ in reasons_counter.most_common(4))

    return ScoredRoute(
        candidate_index=candidate_index,
        distance_m=distance_m,
        duration_s=duration_s,
        segment_lengths=tuple(segment_lengths),
        segment_risks=tuple(segment_risks),
        risk_probability=max(0.0, min(1.0, risk)),
        confidence=max(0.0, min(0.95, 1.0 - uncertainty)),
        uncertainty=uncertainty,
        sparse_fraction=sparse_fraction,
        high_risk_fraction=max(0.0, min(1.0, high_risk_fraction)),
        risk_exposure_m=risk_exposure_m,
        conflicts_present=any(
            "Conflicting recent evidence" in reason for r in segment_risks for reason in r.reasons
        ),
        reasons=reasons,
    )


def profile_cost(scored: ScoredRoute, profile: str) -> float:
    alpha, beta, gamma, delta = PROFILES[profile]
    time_m = scored.duration_s * WALKING_SPEED_MPS
    risk_m = scored.risk_probability * RISK_DISTANCE_EQUIV_M
    uncertainty_m = scored.uncertainty * UNCERTAINTY_DISTANCE_EQUIV_M
    return alpha * scored.distance_m + beta * time_m + gamma * risk_m + delta * uncertainty_m


def assign_route_types(scored_routes: list[ScoredRoute]) -> dict[str, ScoredRoute]:
    """One route type per profile: the candidate minimizing that profile's cost.

    If two profiles select the same candidate, both route types point at it
    (honest: the best available candidate wins twice).
    """
    chosen: dict[str, ScoredRoute] = {}
    for profile in PROFILE_ORDER:
        chosen[profile] = min(scored_routes, key=lambda sr: profile_cost(sr, profile))
    return chosen


def route_warnings(scored: ScoredRoute) -> list[str]:
    warnings: list[str] = []
    if scored.sparse_fraction > SPARSE_WARNING_FRACTION:
        warnings.append(SPARSE_WARNING)
    if scored.conflicts_present:
        warnings.append(CONFLICT_WARNING)
    return warnings
