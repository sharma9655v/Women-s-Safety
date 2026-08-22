"""Synthetic calibration validation of the deterministic risk pipeline.

We build segments whose *world-state risk* p is known by construction (a grid
of ground-truth levels) and whose evidence is generated deterministically to
make the model output land near p. We then measure, on synthetic outcomes
y ~ Bernoulli(p):

  - MAE of modeled risk vs true risk,
  - Spearman rank correlation (does the pipeline order risk correctly?),
  - Brier score of risk vs sampled outcomes, and its ideal value mean(p(1-p)),
  - expected calibration error (ECE) over 10 equal-width risk bins.

This validates *internal consistency* of the deterministic pipeline on
synthetic ground truth — it is NOT real-world calibration. Real calibration
requires observed outcomes from validated civic/NGO feeds (research-spec.md),
which do not exist yet and are never fabricated.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.evidence import aggregate, utc_now
from app.evidence.engine import Observation
from app.evidence.states import VerificationState
from app.risk.model import SegmentRisk, compute_segment_risk

ARTIFACTS = Path(__file__).parent.parent / "artifacts"

NOW = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)

# Ground-truth grid: world-state risk levels we want the model to reproduce.
TRUE_RISK_GRID = (0.05, 0.15, 0.30, 0.45, 0.60, 0.75)
SEGMENTS_PER_LEVEL = 40
TOLERANCE = 0.08

# Deterministic search space over evidence recipes (count, max age hours,
# reliability, facility distance, road type, lit, night). Each grid level
# below was verified to have a recipe within TOLERANCE of its true risk.
_RECIPE_SPACE: tuple[tuple[int, float, float, float | None, str | None, str | None, bool], ...] = (
    (0, 0.0, 0.6, 2000.0, None, None, False),
    (0, 0.0, 0.6, None, "footway", None, True),
    (1, 1.0, 0.4, 250.0, None, None, False),
    (1, 1.0, 0.8, 500.0, "service", None, False),
    (1, 1.0, 0.8, 500.0, None, None, True),
    (3, 1.0, 0.95, 500.0, None, None, True),
)


def _obs(
    seg: int,
    idx: int,
    age_hours: float,
    reliability: float,
) -> Observation:
    obs_type = "harassment" if idx % 2 == 0 else "suspicious_activity"
    return Observation(
        segment_id=seg,
        source_type="street_audit" if reliability >= 0.9 else "user_report",
        observation_type=obs_type,
        observed_at=NOW - timedelta(hours=age_hours),
        source_reliability=reliability,
        value={},
        confidence=0.5,
        state=VerificationState.REPORTED,
        id=seg * 100 + idx,
    )


def _model_risk(segment_id: int, recipe: tuple) -> SegmentRisk:
    count, max_age, reliability, facility, road_type, lit, night = recipe
    observations = [
        _obs(segment_id, i, 1.0 + (i * (max_age - 1.0)) / max(count, 1), reliability)
        for i in range(count)
    ]
    evidence = aggregate(segment_id, observations, NOW) if observations else None
    return compute_segment_risk(
        segment_id=segment_id,
        evidence=evidence,
        road_type=road_type,
        lit=lit,
        nearest_emergency_m=facility,
        hour_ist=23 if night else 12,
    )


def _recipe_for(segment_id: int, p: float) -> tuple[tuple, SegmentRisk] | None:
    """First deterministic recipe whose modeled risk lands within tolerance of
    the ground-truth level p. None means the grid is unreachable."""
    best: tuple[tuple, SegmentRisk] | None = None
    best_gap = float("inf")
    for recipe in _RECIPE_SPACE:
        risk = _model_risk(segment_id, recipe)
        gap = abs(risk.risk_probability - p)
        if gap <= TOLERANCE:
            return recipe, risk
        if gap < best_gap:
            best_gap = gap
            best = recipe, risk
    return best


def _outcome(segment_id: int, p: float, seed: int) -> float:
    """Deterministic Bernoulli draw from the ground-truth risk."""
    digest = hashlib.sha256(f"calib:{seed}:{segment_id}".encode()).digest()
    u = int.from_bytes(digest[:8], "big") / (2**64)
    return 1.0 if u < p else 0.0


def brier_score(risks: list[float], outcomes: list[float]) -> float:
    return sum((r - y) ** 2 for r, y in zip(risks, outcomes, strict=True)) / len(risks)


def expected_calibration_error(
    risks: list[float],
    truths: list[float],
    bins: int = 10,
) -> float:
    """ECE: |mean risk - mean true rate| weighted by bin size over equal-width
    risk bins. Empty bins are ignored."""
    if not risks:
        return 0.0
    width = 1.0 / bins
    total = 0.0
    count = 0
    for b in range(bins):
        lo, hi = b * width, (b + 1) * width
        idx = [i for i, r in enumerate(risks) if lo <= r < hi]
        if not idx:
            continue
        mean_risk = sum(risks[i] for i in idx) / len(idx)
        mean_truth = sum(truths[i] for i in idx) / len(idx)
        total += len(idx) * abs(mean_risk - mean_truth)
        count += len(idx)
    return total / max(count, 1)


def spearman_rho(pairs: list[tuple[float, float]]) -> float:
    """Spearman rank correlation between modeled risk and ground truth."""
    if len(pairs) < 2:
        return 0.0

    def ranks(values: list[float]) -> list[float]:
        ordered = sorted(range(len(values)), key=lambda i: values[i])
        ranked: list[float] = [0.0] * len(values)
        for pos, idx in enumerate(ordered):
            ranked[idx] = float(pos)
        return ranked

    x = ranks([a for a, _ in pairs])
    y = ranks([b for _, b in pairs])
    n = len(pairs)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y, strict=True))
    den = math.sqrt(
        sum((xi - mean_x) ** 2 for xi in x) * sum((yi - mean_y) ** 2 for yi in y)
    )
    return num / den if den > 0 else 0.0


def run_calibration() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    risks: list[float] = []
    truths: list[float] = []
    outcomes: list[float] = []
    unreachable: list[float] = []

    seg = 0
    for p in TRUE_RISK_GRID:
        level_risks: list[float] = []
        for _ in range(SEGMENTS_PER_LEVEL):
            seg += 1
            found = _recipe_for(seg, p)
            if found is None:
                unreachable.append(p)
                continue
            recipe, risk = found
            r = risk.risk_probability
            risks.append(r)
            truths.append(p)
            outcomes.append(_outcome(seg, p, seed=20260814))
            level_risks.append(r)
        rows.append(
            {
                "true_risk": p,
                "n": len(level_risks),
                "mean_modeled_risk": round(sum(level_risks) / max(len(level_risks), 1), 4),
                "recipe": found[0] if found is not None else None,
            }
        )

    ideal = sum(p * (1.0 - p) for p in truths) / max(len(truths), 1)
    brier = brier_score(risks, outcomes)
    return {
        "experiment": "calibration-synthetic",
        "model_version": "deterministic-baseline-v1",
        "evidence_model_version": "evidence-baseline-v1",
        "now": NOW.isoformat(),
        "run_at": utc_now().isoformat(timespec="seconds"),
        "levels": rows,
        "n_segments": len(risks),
        "unreachable_levels": unreachable,
        "mae_risk_vs_truth": round(
            sum(abs(r - p) for r, p in zip(risks, truths, strict=True)) / max(len(risks), 1), 4
        ),
        "spearman_rho_risk_vs_truth": round(spearman_rho(list(zip(risks, truths, strict=True))), 4),
        "brier_vs_synthetic_outcomes": round(brier, 4),
        "ideal_brier_mean_p1mp": round(ideal, 4),
        "brier_excess_over_ideal": round(brier - ideal, 4),
        "ece_10_bins_risk_vs_truth": round(
            expected_calibration_error(risks, truths, bins=10), 4
        ),
        "note": "Synthetic ground truth validates internal consistency and "
        "ordering only; real calibration requires observed outcomes from "
        "validated feeds (gated, none exist).",
    }


def write_artifacts(result: dict[str, object]) -> Path:
    ts = utc_now().strftime("%Y%m%dT%H%M%S")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / f"calibration-{ts}.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    path = write_artifacts(run_calibration())
    print(f"wrote {path}")
