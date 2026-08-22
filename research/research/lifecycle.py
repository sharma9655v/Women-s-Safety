"""Critical experiment (research-spec.md): the streetlight lifecycle.

Timeline on one synthetic segment (road_type=footway, no facilities):
  t0   verified-working observation (city_data, VERIFIED, working=true)
  t30  simulated failure: street_audit working=false + 1 user report
  t31  +2 more independent user reports
  t60  verified repair: street_audit working=true (VERIFIED)
  t120 old failure evidence continues to age

Measured at every step (research-spec.md questions):
  1. old-evidence weight (freshness of the t0 observation)
  2. uncertainty (1 - confidence)
  3. route-ranking shift on a synthetic two-candidate choice
  4. confidence restore after verified repair
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.evidence import aggregate, utc_now
from app.evidence.engine import Observation
from app.evidence.states import VerificationState
from app.risk.model import SegmentRisk, compute_segment_risk

ARTIFACTS = Path(__file__).parent.parent / "artifacts"

T0 = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def _obs(
    seg: int,
    obs_type: str,
    at: datetime,
    source: str,
    reliability: float,
    value: dict[str, object] | None = None,
    state: VerificationState = VerificationState.REPORTED,
) -> Observation:
    return Observation(
        segment_id=seg,
        source_type=source,
        observation_type=obs_type,
        observed_at=at,
        source_reliability=reliability,
        value=value or {},
        confidence=0.5,
        state=state,
    )


@dataclass(frozen=True)
class Step:
    label: str
    day: int
    observations: tuple[Observation, ...]


def build_timeline() -> list[Step]:
    return [
        Step(
            "t0_verified_working",
            0,
            (
                _obs(
                    1,
                    "streetlight_not_working",
                    T0,
                    "city_data",
                    0.9,
                    {"working": True},
                    VerificationState.VERIFIED,
                ),
            ),
        ),
        Step(
            "t30_failure_reported",
            30,
            (
                _obs(
                    1,
                    "streetlight_not_working",
                    T0,
                    "city_data",
                    0.9,
                    {"working": True},
                    VerificationState.VERIFIED,
                ),
                _obs(
                    1,
                    "streetlight_not_working",
                    T0 + timedelta(days=30),
                    "street_audit",
                    0.95,
                    {"working": False},
                ),
                _obs(1, "streetlight_not_working", T0 + timedelta(days=30), "user_report", 0.6),
            ),
        ),
        Step(
            "t31_multiple_reports",
            31,
            (
                _obs(
                    1,
                    "streetlight_not_working",
                    T0,
                    "city_data",
                    0.9,
                    {"working": True},
                    VerificationState.VERIFIED,
                ),
                _obs(
                    1,
                    "streetlight_not_working",
                    T0 + timedelta(days=30),
                    "street_audit",
                    0.95,
                    {"working": False},
                ),
                _obs(1, "streetlight_not_working", T0 + timedelta(days=30), "user_report", 0.6),
                _obs(1, "streetlight_not_working", T0 + timedelta(days=31), "user_report", 0.6),
                _obs(1, "streetlight_not_working", T0 + timedelta(days=31), "user_report", 0.6),
            ),
        ),
        Step(
            "t60_verified_repair",
            60,
            (
                _obs(
                    1,
                    "streetlight_not_working",
                    T0,
                    "city_data",
                    0.9,
                    {"working": True},
                    VerificationState.VERIFIED,
                ),
                _obs(
                    1,
                    "streetlight_not_working",
                    T0 + timedelta(days=30),
                    "street_audit",
                    0.95,
                    {"working": False},
                ),
                _obs(1, "streetlight_not_working", T0 + timedelta(days=30), "user_report", 0.6),
                _obs(1, "streetlight_not_working", T0 + timedelta(days=31), "user_report", 0.6),
                _obs(1, "streetlight_not_working", T0 + timedelta(days=31), "user_report", 0.6),
                _obs(
                    1,
                    "streetlight_not_working",
                    T0 + timedelta(days=60),
                    "street_audit",
                    0.95,
                    {"working": True},
                    VerificationState.VERIFIED,
                ),
            ),
        ),
        Step(
            "t120_failure_decayed",
            120,
            (
                _obs(
                    1,
                    "streetlight_not_working",
                    T0,
                    "city_data",
                    0.9,
                    {"working": True},
                    VerificationState.VERIFIED,
                ),
                _obs(
                    1,
                    "streetlight_not_working",
                    T0 + timedelta(days=30),
                    "street_audit",
                    0.95,
                    {"working": False},
                ),
                _obs(1, "streetlight_not_working", T0 + timedelta(days=30), "user_report", 0.6),
                _obs(1, "streetlight_not_working", T0 + timedelta(days=31), "user_report", 0.6),
                _obs(1, "streetlight_not_working", T0 + timedelta(days=31), "user_report", 0.6),
                _obs(
                    1,
                    "streetlight_not_working",
                    T0 + timedelta(days=60),
                    "street_audit",
                    0.95,
                    {"working": True},
                    VerificationState.VERIFIED,
                ),
            ),
        ),
    ]


def _measure(step: Step, now: datetime) -> dict[str, object]:
    evidence = aggregate(1, list(step.observations), now)
    risk: SegmentRisk = compute_segment_risk(
        segment_id=1,
        evidence=evidence,
        road_type="footway",
        lit=None,
        nearest_emergency_m=None,
        hour_ist=12,
    )
    summary = evidence.by_type.get("streetlight_not_working")
    # Old-evidence weight: freshness of the t0 VERIFIED observation.
    t0_obs = next(o for o in step.observations if o.observed_at == T0)
    from app.evidence import freshness

    return {
        "day": step.day,
        "state_counts": dict(summary.state_counts) if summary else {},
        "overall_freshness": evidence.overall_freshness,
        "overall_confidence": evidence.overall_confidence,
        "t0_freshness": freshness(t0_obs.observed_at, now, "streetlight_not_working"),
        "uncertainty": risk.uncertainty,
        "risk": risk.risk_probability,
        "reasons": list(risk.reasons),
        "conflicts": evidence.conflicts,
    }


def run_lifecycle() -> dict[str, object]:
    timeline = build_timeline()
    steps: list[dict[str, object]] = []
    for step in timeline:
        now = T0 + timedelta(days=step.day)
        steps.append({"label": step.label, **_measure(step, now)})
    return {
        "experiment": "streetlight-lifecycle",
        "model_version": "deterministic-baseline-v1",
        "evidence_model_version": "evidence-baseline-v1",
        "t0": T0.isoformat(),
        "run_at": utc_now().isoformat(timespec="seconds"),
        "steps": steps,
    }


def write_artifacts(result: dict[str, object]) -> tuple[Path, Path]:
    ts = utc_now().strftime("%Y%m%dT%H%M%S")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    json_path = ARTIFACTS / f"lifecycle-{ts}.json"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Streetlight lifecycle experiment (recorded run)",
        "",
        f"- t0: {result['t0']}",
        f"- run_at: {result['run_at']}",
        f"- model_version: {result['model_version']}",
        "",
        "| step | day | t0 freshness | overall confidence | uncertainty | risk | conflicts |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in result["steps"]:  # type: ignore[union-attr]
        lines.append(
            f"| {s['label']} | {s['day']} | {s['t0_freshness']:.3f} | "
            f"{s['overall_confidence']:.3f} | {s['uncertainty']:.3f} | {s['risk']:.4f} | "
            f"{s['conflicts']} |"
        )
    md_path = ARTIFACTS / f"lifecycle-{ts}.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


if __name__ == "__main__":
    json_path, md_path = write_artifacts(run_lifecycle())
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
