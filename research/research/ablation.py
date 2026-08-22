"""Leave-one-out ablation of the deterministic risk pipeline.

For one synthetic "hot corridor" segment we measure, for every component of
the deterministic risk model (incident evidence, lighting evidence, emergency
facility proximity, road infrastructure, time-of-day), the marginal risk it
contributes and whether removing it changes the winning candidate under the
safety_priority route profile (route stability).

Fidelity: `_component_risks` mirrors `app.risk.model.compute_segment_risk`
exactly (constants imported from production code), and a test asserts the
recombination reproduces the production risk bit-for-bit. No production code
is modified for this experiment.

Confidence is evidence-volume based (not component based): ablating facility /
road / lit-tag components changes risk but not confidence — recorded honestly.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.evidence import SegmentEvidence, aggregate, utc_now
from app.evidence.engine import Observation
from app.evidence.states import VerificationState
from app.risk.model import (
    FACILITY_CUTOFF_M,
    FACILITY_LOGISTIC_CENTER_M,
    FACILITY_LOGISTIC_SLOPE_M,
    INCIDENT_SCALE,
    INCIDENT_TYPES,
    LIGHTING_SCALE,
    LIGHTING_TYPES,
    LIT_TAG_NIGHT_REDUCTION,
    NIGHT_HOURS,
    NIGHT_MULTIPLIER,
    RISK_W_FACILITY,
    RISK_W_INCIDENT,
    RISK_W_LIGHTING,
    RISK_W_ROAD,
    ROAD_NIGHT_RISK,
    UNLIT_TAG_NIGHT_INCREASE,
    SegmentRisk,
    compute_segment_risk,
)

ARTIFACTS = Path(__file__).parent.parent / "artifacts"

NOW = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)

COMPONENTS = ("incident", "lighting", "facility", "road")


def _logistic_facility_risk(distance_m: float) -> float:
    return 1.0 / (
        1.0 + math.exp((FACILITY_LOGISTIC_CENTER_M - distance_m) / FACILITY_LOGISTIC_SLOPE_M)
    )


def _component_risks(
    evidence: SegmentEvidence | None,
    road_type: str | None,
    lit: str | None,
    nearest_emergency_m: float | None,
    hour_ist: int,
) -> dict[str, float]:
    """Raw per-component risks before weighting — mirrors compute_segment_risk."""
    is_night = hour_ist in NIGHT_HOURS

    incident_score = 0.0
    lighting_score = 0.0
    if evidence is not None:
        for obs_type in INCIDENT_TYPES:
            summary = evidence.by_type.get(obs_type)
            if summary is not None:
                incident_score += summary.score
        for obs_type in LIGHTING_TYPES:
            summary = evidence.by_type.get(obs_type)
            if summary is not None:
                lighting_score += summary.score
    risk_incident = 1.0 - math.exp(-INCIDENT_SCALE * incident_score)

    risk_lighting = 1.0 - math.exp(-LIGHTING_SCALE * lighting_score)
    if is_night:
        if lit == "yes":
            risk_lighting *= LIT_TAG_NIGHT_REDUCTION
        elif lit == "no":
            risk_lighting *= UNLIT_TAG_NIGHT_INCREASE
    else:
        risk_lighting *= 0.5

    risk_facility = (
        _logistic_facility_risk(nearest_emergency_m)
        if nearest_emergency_m is not None
        else _logistic_facility_risk(FACILITY_CUTOFF_M)
    )

    risk_road = ROAD_NIGHT_RISK.get(road_type or "", 0.0)
    if risk_road and is_night:
        risk_road *= 1.5
    elif risk_road:
        risk_road *= 0.5

    return {
        "incident": risk_incident,
        "lighting": min(risk_lighting, 1.0),
        "facility": risk_facility,
        "road": risk_road,
    }


def recombined_risk(
    evidence: SegmentEvidence | None,
    road_type: str | None,
    lit: str | None,
    nearest_emergency_m: float | None,
    hour_ist: int,
) -> float:
    """Weighted recombination of the components (ablation recomposition)."""
    components = _component_risks(evidence, road_type, lit, nearest_emergency_m, hour_ist)
    weights = {
        "incident": RISK_W_INCIDENT,
        "lighting": RISK_W_LIGHTING,
        "facility": RISK_W_FACILITY,
        "road": RISK_W_ROAD,
    }
    combined = sum(weights[c] * components[c] for c in COMPONENTS)
    if hour_ist in NIGHT_HOURS:
        combined *= NIGHT_MULTIPLIER
    return max(0.0, min(1.0, combined))


def _obs(
    seg: int,
    obs_type: str,
    age_hours: float,
    source: str = "user_report",
    reliability: float = 0.7,
    value: dict[str, object] | None = None,
    state: VerificationState = VerificationState.REPORTED,
) -> Observation:
    return Observation(
        segment_id=seg,
        source_type=source,
        observation_type=obs_type,
        observed_at=NOW - timedelta(hours=age_hours),
        source_reliability=reliability,
        value=value or {},
        confidence=0.5,
        state=state,
        id=seg * 1000 + int(age_hours),
    )


def _marginal_contributions(
    evidence: SegmentEvidence | None,
    *,
    road_type: str | None,
    lit: str | None,
    nearest_emergency_m: float | None,
    hour_ist: int,
) -> dict[str, float]:
    """Signed risk deltas when each component is removed (leave-one-out).

    The night multiplier applies to the whole pre-multiplier sum, so the
    ablated risk removes the component from that sum *before* scaling.
    """
    components = _component_risks(evidence, road_type, lit, nearest_emergency_m, hour_ist)
    weights = {
        "incident": RISK_W_INCIDENT,
        "lighting": RISK_W_LIGHTING,
        "facility": RISK_W_FACILITY,
        "road": RISK_W_ROAD,
    }
    is_night = hour_ist in NIGHT_HOURS
    pre = sum(weights[c] * components[c] for c in COMPONENTS)
    multiplier = NIGHT_MULTIPLIER if is_night else 1.0
    full = max(0.0, min(1.0, pre * multiplier))
    contributions: dict[str, float] = {}
    for c in COMPONENTS:
        ablated = max(0.0, min(1.0, (pre - weights[c] * components[c]) * multiplier))
        contributions[c] = full - ablated
    return contributions


def _full_risk(
    segment_id: int,
    observations: list[Observation],
    *,
    road_type: str | None,
    lit: str | None,
    nearest_emergency_m: float | None,
    hour_ist: int,
) -> tuple[SegmentRisk, dict[str, float]]:
    evidence = aggregate(segment_id, observations, NOW)
    risk = compute_segment_risk(
        segment_id=segment_id,
        evidence=evidence,
        road_type=road_type,
        lit=lit,
        nearest_emergency_m=nearest_emergency_m,
        hour_ist=hour_ist,
    )
    contributions = _marginal_contributions(
        evidence,
        road_type=road_type,
        lit=lit,
        nearest_emergency_m=nearest_emergency_m,
        hour_ist=hour_ist,
    )
    return risk, contributions


# --- scenarios ---------------------------------------------------------------


def _corridor_scenarios() -> dict[str, object]:
    scenarios: dict[str, object] = {}
    # Tuned so the full risk stays below the 1.0 clamp: leave-one-out deltas
    # are then exact (no clamping hides any contribution).
    corridor_obs = [
        _obs(1, "harassment", age_hours=2, reliability=0.8),
        _obs(
            1,
            "streetlight_not_working",
            age_hours=3,
            source="street_audit",
            reliability=0.95,
            value={"working": False},
        ),
    ]
    risk, contributions = _full_risk(
        1, corridor_obs, road_type="footway", lit="no", nearest_emergency_m=850.0, hour_ist=23
    )
    total = sum(contributions.values())
    scenarios["corridor_night"] = {
        "risk": risk.risk_probability,
        "confidence": risk.confidence,
        "uncertainty": risk.uncertainty,
        "reasons": list(risk.reasons),
        "marginal_contribution": contributions,
        "share_of_risk": {c: round(v / max(total, 1e-9), 4) for c, v in contributions.items()},
    }

    # Daytime twin: same evidence, hour 12 — isolates the time-of-day component.
    day_risk, day_contrib = _full_risk(
        1, corridor_obs, road_type="footway", lit="no", nearest_emergency_m=850.0, hour_ist=12
    )
    scenarios["corridor_day"] = {
        "risk": day_risk.risk_probability,
        "confidence": day_risk.confidence,
        "reasons": list(day_risk.reasons),
        "marginal_contribution": day_contrib,
        "night_over_day_ratio": round(
            risk.risk_probability / max(day_risk.risk_probability, 1e-9), 3
        ),
    }

    # Sparse-data twin: same physical context, no evidence — the honest
    # baseline the evidence components must move risk above.
    sparse_risk, sparse_contrib = _full_risk(
        2, [], road_type="footway", lit="no", nearest_emergency_m=850.0, hour_ist=23
    )
    scenarios["corridor_night_no_evidence"] = {
        "risk": sparse_risk.risk_probability,
        "confidence": sparse_risk.confidence,
        "reasons": list(sparse_risk.reasons),
        "marginal_contribution": sparse_contrib,
    }
    return scenarios


def _route_stability() -> dict[str, object]:
    """Does leave-one-out ablation change which candidate wins the safety
    profile? Candidates share distance/duration (ranking driven by risk)."""

    candidates = [
        {
            "name": "A_incident_heavy",
            "obs": [
                _obs(11, "harassment", age_hours=1, reliability=0.9),
                _obs(11, "harassment", age_hours=3, reliability=0.8),
                _obs(11, "suspicious_activity", age_hours=2, reliability=0.7),
            ],
            "road_type": "footway",
            "lit": "no",
            "facility": 850.0,
        },
        {
            "name": "B_lighting_and_road",
            "obs": [
                _obs(
                    12,
                    "streetlight_not_working",
                    age_hours=2,
                    reliability=0.95,
                    value={"working": False},
                ),
                _obs(12, "poor_lighting", age_hours=4, reliability=0.6),
            ],
            "road_type": "footway",
            "lit": "no",
            "facility": 2500.0,
        },
        {
            "name": "C_facility_protected",
            "obs": [],
            "road_type": "service",
            "lit": "yes",
            "facility": 350.0,
        },
    ]
    results: list[dict[str, object]] = []
    for cand in candidates:
        risk, contributions = _full_risk(
            cand["obs"][0].segment_id if cand["obs"] else 20,
            cand["obs"],
            road_type=cand["road_type"],
            lit=cand["lit"],
            nearest_emergency_m=cand["facility"],
            hour_ist=23,
        )
        results.append(
            {
                "candidate": cand["name"],
                "risk": risk.risk_probability,
                "confidence": risk.confidence,
                "reasons": list(risk.reasons),
                "marginal_contribution": contributions,
            }
        )
    # Safety-profile ranking with identical distance/duration: the candidate
    # with the lowest risk wins. Removing a component lowers risk only for
    # candidates that have it — ranking flips reveal which evidence the
    # recommendation depends on (route stability).
    winner_full = min(range(len(candidates)), key=lambda i: _candidate_risk(i, candidates, None))
    winners_ablated: dict[str, int] = {}
    for c in COMPONENTS:
        winners_ablated[c] = min(
            range(len(candidates)), key=lambda i: _candidate_risk(i, candidates, c)
        )
    stability = {
        "winner_full_risk": winner_full,
        "winner_per_ablation": winners_ablated,
        "ranking_flips": sorted(
            {
                c: winners_ablated[c]
                for c in COMPONENTS
                if winners_ablated[c] != winner_full
            }.items()
        ),
    }
    return {"candidates": results, "stability": stability}


def _candidate_risk(
    index: int, candidates: list[dict[str, object]], ablated: str | None
) -> float:
    cand = candidates[index]
    observations = cand["obs"]  # type: ignore[arg-type]
    segment_id = observations[0].segment_id if observations else 20 + index
    evidence = aggregate(segment_id, observations, NOW) if observations else None
    road_type = cand["road_type"]  # type: ignore[arg-type]
    lit = cand["lit"]  # type: ignore[arg-type]
    nearest_emergency_m = cand["facility"]  # type: ignore[arg-type]
    risk = compute_segment_risk(
        segment_id=segment_id,
        evidence=evidence,
        road_type=road_type,
        lit=lit,
        nearest_emergency_m=nearest_emergency_m,
        hour_ist=23,
    )
    if ablated is None:
        return risk.risk_probability
    components = _component_risks(evidence, road_type, lit, nearest_emergency_m, 23)
    weights = {
        "incident": RISK_W_INCIDENT,
        "lighting": RISK_W_LIGHTING,
        "facility": RISK_W_FACILITY,
        "road": RISK_W_ROAD,
    }
    combined = sum(weights[c] * components[c] for c in COMPONENTS if c != ablated)
    return max(0.0, min(1.0, combined * NIGHT_MULTIPLIER))


def run_ablation() -> dict[str, object]:
    return {
        "experiment": "ablation-leave-one-out",
        "model_version": "deterministic-baseline-v1",
        "evidence_model_version": "evidence-baseline-v1",
        "now": NOW.isoformat(),
        "run_at": utc_now().isoformat(timespec="seconds"),
        "components": list(COMPONENTS),
        "scenarios": _corridor_scenarios(),
        "route_stability": _route_stability(),
        "note": "Confidence is evidence-volume based; component ablation changes "
        "risk only, never confidence. Shares are exact only when no clamping occurs.",
    }


def write_artifacts(result: dict[str, object]) -> Path:
    ts = utc_now().strftime("%Y%m%dT%H%M%S")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / f"ablation-{ts}.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    path = write_artifacts(run_ablation())
    print(f"wrote {path}")
