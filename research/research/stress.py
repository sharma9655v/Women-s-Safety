"""Stress tests: stale, missing, noisy, conflicting evidence; day vs night.

Each scenario runs the deterministic risk model on a synthetic segment with
exactly the evidence described. Values recorded in the artifact are whatever
the model actually produced — no expectations are adjusted afterwards.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.evidence import aggregate, utc_now
from app.evidence.engine import Observation
from app.evidence.states import VerificationState
from app.risk.model import SegmentRisk, compute_segment_risk

ARTIFACTS = Path(__file__).parent.parent / "artifacts"

NOW = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)


def _obs(
    seg: int,
    obs_type: str,
    age_hours: float,
    source: str = "user_report",
    reliability: float = 0.6,
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
        id=seg * 100 + int(age_hours),
    )


def _risk(segment_id: int, observations: list[Observation], hour_ist: int) -> SegmentRisk:
    evidence = aggregate(segment_id, observations, NOW)
    return compute_segment_risk(
        segment_id=segment_id,
        evidence=evidence,
        road_type="footway",
        lit=None,
        nearest_emergency_m=None,
        hour_ist=hour_ist,
    )


def run_stress() -> dict[str, object]:
    scenarios: dict[str, object] = {}

    missing = _risk(1, [], hour_ist=12)
    scenarios["missing_evidence"] = {
        "risk": missing.risk_probability,
        "confidence": missing.confidence,
        "uncertainty": missing.uncertainty,
        "reasons": list(missing.reasons),
    }

    stale = _risk(2, [_obs(2, "harassment", age_hours=600 * 24)], hour_ist=12)
    scenarios["stale_single_report_600d"] = {
        "risk": stale.risk_probability,
        "confidence": stale.confidence,
        "reasons": list(stale.reasons),
    }

    fresh = _risk(3, [_obs(3, "harassment", age_hours=2)], hour_ist=12)
    scenarios["fresh_single_report_2h"] = {
        "risk": fresh.risk_probability,
        "confidence": fresh.confidence,
        "reasons": list(fresh.reasons),
    }

    noisy = _risk(
        4,
        [
            _obs(4, "harassment", age_hours=1, source="user_report", reliability=0.6),
            _obs(4, "harassment", age_hours=2, source="user_report", reliability=0.6),
            _obs(4, "harassment", age_hours=3, source="user_report", reliability=0.6),
        ],
        hour_ist=12,
    )
    scenarios["noisy_three_same_source_weak"] = {
        "risk": noisy.risk_probability,
        "confidence": noisy.confidence,
        "reasons": list(noisy.reasons),
    }

    confirmed = _risk(
        5,
        [
            _obs(5, "harassment", age_hours=1, source="user_report", reliability=0.6),
            _obs(5, "harassment", age_hours=2, source="street_audit", reliability=0.95),
        ],
        hour_ist=12,
    )
    scenarios["corroborated_two_sources"] = {
        "risk": confirmed.risk_probability,
        "confidence": confirmed.confidence,
        "reasons": list(confirmed.reasons),
    }

    conflicting = _risk(
        6,
        [
            _obs(
                6,
                "streetlight_not_working",
                age_hours=1,
                source="street_audit",
                reliability=0.95,
                value={"working": False},
            ),
            _obs(
                6,
                "streetlight_not_working",
                age_hours=2,
                source="city_data",
                reliability=0.9,
                value={"working": True},
            ),
        ],
        hour_ist=12,
    )
    scenarios["conflicting_evidence"] = {
        "risk": conflicting.risk_probability,
        "confidence": conflicting.confidence,
        "uncertainty": conflicting.uncertainty,
        "reasons": list(conflicting.reasons),
    }

    night_segment = _risk(7, [_obs(7, "harassment", age_hours=1)], hour_ist=23)
    day_segment = _risk(7, [_obs(7, "harassment", age_hours=1)], hour_ist=12)
    scenarios["day_vs_night_same_evidence"] = {
        "day": {"risk": day_segment.risk_probability, "reasons": list(day_segment.reasons)},
        "night": {"risk": night_segment.risk_probability, "reasons": list(night_segment.reasons)},
        "night_over_day_ratio": round(
            night_segment.risk_probability / max(day_segment.risk_probability, 1e-9), 3
        ),
    }

    lit_night = _risk(
        8,
        [],
        hour_ist=23,
    )
    scenarios["night_without_evidence_lit_vs_unlit"] = {
        "reasons": list(lit_night.reasons),
        "note": "OSM lit tag only affects lighting risk, which needs lighting "
        "evidence; no evidence -> unchanged",
    }

    return {
        "experiment": "stress-evidence",
        "model_version": "deterministic-baseline-v1",
        "evidence_model_version": "evidence-baseline-v1",
        "now": NOW.isoformat(),
        "run_at": utc_now().isoformat(timespec="seconds"),
        "scenarios": scenarios,
    }


def write_artifacts(result: dict[str, object]) -> Path:
    ts = utc_now().strftime("%Y%m%dT%H%M%S")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / f"stress-{ts}.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    path = write_artifacts(run_stress())
    print(f"wrote {path}")
