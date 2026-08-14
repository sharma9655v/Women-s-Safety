"""Baselines B1-B5 over real OSRM candidates and real PostGIS evidence.

B1 shortest                : choose the minimum-distance candidate.
B2 fastest                 : choose the minimum-duration candidate.
B3 static safety           : balanced cost, risk computed with all evidence
                             treated as fresh (freshness ignored).
B4 dynamic safety          : balanced cost, risk with real freshness.
B5 dynamic + uncertainty   : B4 with the uncertainty weight doubled.

Metrics recorded per pair and aggregated across pairs:
  - risk reduction (%) of B4 vs B1 on the *same* evidence
  - time penalty (%) of B4 vs B2
  - distance penalty (%) of B4 vs B1
Requires the live stack (PostGIS + OSRM) for the real-data run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.api.routes import _facility_bbox, _match_all, _midpoint
from app.config import settings
from app.evidence import aggregate, get_evidence_store
from app.evidence.engine import replace
from app.facilities import get_facilities_store
from app.risk.model import compute_segment_risk
from app.risk.routing import (
    PROFILES,
    RISK_DISTANCE_EQUIV_M,
    UNCERTAINTY_DISTANCE_EQUIV_M,
    WALKING_SPEED_MPS,
    nearest_emergency_m,
    score_candidate,
    segment_length_m,
)
from app.routing import OsrmClient
from app.schemas import LatLon
from app.segments import get_segments_store

ARTIFACTS = Path(__file__).parent.parent / "artifacts"

# B3/B4/B5 model a *safety-aware* recommender: the safety_priority profile
# (research question: safety-aware routing vs shortest/fastest baselines).
SAFETY_WEIGHTS = PROFILES["safety_priority"]
UNCERTAINTY_AWARE_WEIGHTS = (0.6, 1.0, 2.0, 2.0)


@dataclass(frozen=True)
class Pair:
    name: str
    origin: LatLon
    destination: LatLon


OD_PAIRS = [
    Pair("seeded_area_day", LatLon(lat=28.61, lon=77.23), LatLon(lat=28.63, lon=77.21)),
    Pair("connaught_place", LatLon(lat=28.6314, lon=77.2167), LatLon(lat=28.6139, lon=77.209)),
    Pair("karol_bagh", LatLon(lat=28.6519, lon=77.1908), LatLon(lat=28.6139, lon=77.209)),
]


def _baseline_cost(
    weights: tuple[float, float, float, float],
    distance_m: float,
    duration_s: float,
    risk: float,
    uncertainty: float,
) -> float:
    return (
        weights[0] * distance_m
        + weights[1] * duration_s * WALKING_SPEED_MPS
        + weights[2] * risk * RISK_DISTANCE_EQUIV_M
        + weights[3] * uncertainty * UNCERTAINTY_DISTANCE_EQUIV_M
    )


def _candidate_metrics(
    distance_m: float,
    duration_s: float,
    segment_lengths: list[float],
    dynamic_risks: list[object],
    static_risks: list[object],
) -> dict[str, float]:
    dynamic = score_candidate(0, distance_m, duration_s, segment_lengths, dynamic_risks)
    static = score_candidate(0, distance_m, duration_s, segment_lengths, static_risks)
    return {
        "distance_m": distance_m,
        "duration_s": duration_s,
        "risk_dynamic": dynamic.risk_probability,
        "uncertainty_dynamic": dynamic.uncertainty,
        "risk_static": static.risk_probability,
        "uncertainty_static": static.uncertainty,
        "safety_dynamic": 1.0 - dynamic.risk_probability,
    }


def run_baselines(hour_ist: int = 12, od_pairs: list[Pair] | None = None) -> dict[str, object]:
    client = OsrmClient(settings.osrm_base_url)
    segments = get_segments_store()
    evidence = get_evidence_store()
    facilities = get_facilities_store()
    pairs = od_pairs or OD_PAIRS

    pair_results: list[dict[str, object]] = []
    for pair in pairs:
        candidates = client.routes(pair.origin, pair.destination, "walking")
        if len(candidates) < 2:
            continue
        matched, nearby_by_id = _match_all(candidates, segments)
        all_segment_ids = [seg_id for ids in matched for seg_id in ids]
        observations = evidence.observations_for_segments(all_segment_ids)
        now = datetime.now(UTC)
        evidence_by_segment: dict[int, object] = {}
        static_by_segment: dict[int, object] = {}
        for seg_id in all_segment_ids:
            obs = observations.get(seg_id, [])
            evidence_by_segment[seg_id] = aggregate(seg_id, obs, now)
            static_by_segment[seg_id] = aggregate(
                seg_id, [replace(o, observed_at=now) for o in obs], now
            )

        facility_bbox = _facility_bbox(candidates)
        nearby_facilities = facilities.within_bbox(
            *facility_bbox, types=("police", "hospital", "fire_station")
        )

        candidate_metrics: list[dict[str, float]] = []
        for candidate, segment_ids in zip(candidates, matched, strict=True):
            dynamic_risks = []
            static_risks = []
            lengths: list[float] = []
            for seg_id in segment_ids:
                road_segment = nearby_by_id.get(seg_id)
                midpoint = _midpoint(road_segment.geometry) if road_segment is not None else None
                facility_distance = (
                    nearest_emergency_m(midpoint[0], midpoint[1], nearby_facilities)
                    if midpoint
                    else None
                )
                common = {
                    "segment_id": seg_id,
                    "road_type": road_segment.road_type if road_segment else None,
                    "lit": road_segment.lit if road_segment else None,
                    "nearest_emergency_m": facility_distance,
                    "hour_ist": hour_ist,
                }
                dynamic_risks.append(
                    compute_segment_risk(evidence=evidence_by_segment.get(seg_id), **common)
                )
                static_risks.append(
                    compute_segment_risk(evidence=static_by_segment.get(seg_id), **common)
                )
                lengths.append(segment_length_m(road_segment.geometry) if road_segment else 0.0)
            candidate_metrics.append(
                _candidate_metrics(
                    candidate.distance_m,
                    candidate.duration_s,
                    lengths,
                    dynamic_risks,
                    static_risks,
                )
            )

        chosen, comparisons = _rank_baselines(candidate_metrics)
        pair_results.append(
            {
                "pair": pair.name,
                "origin": (pair.origin.lat, pair.origin.lon),
                "destination": (pair.destination.lat, pair.destination.lon),
                "candidates": candidate_metrics,
                "chosen": chosen,
                "comparisons": comparisons,
            }
        )

    client.close()

    n = max(len(pair_results), 1)
    agg = {
        "pairs_compared": len(pair_results),
        "mean_risk_reduction_pct_b4_vs_b1": sum(
            p["comparisons"]["risk_reduction_pct_b4_vs_b1"] for p in pair_results
        )
        / n,
        "mean_time_penalty_pct_b4_vs_b2": sum(
            p["comparisons"]["time_penalty_pct_b4_vs_b2"] for p in pair_results
        )
        / n,
        "mean_distance_penalty_pct_b4_vs_b1": sum(
            p["comparisons"]["distance_penalty_pct_b4_vs_b1"] for p in pair_results
        )
        / n,
    }
    return {
        "experiment": "baselines-b1-b5",
        "model_version": "deterministic-baseline-v1",
        "evidence_model_version": "evidence-baseline-v1",
        "hour_ist": hour_ist,
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "pairs": pair_results,
        "aggregates": agg,
    }


def _rank_baselines(
    candidate_metrics: list[dict[str, float]],
) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    def pick(weights: tuple[float, float, float, float], risk_key: str, unc_key: str) -> int:
        costs = [
            _baseline_cost(weights, m["distance_m"], m["duration_s"], m[risk_key], m[unc_key])
            for m in candidate_metrics
        ]
        return costs.index(min(costs))

    b1 = min(range(len(candidate_metrics)), key=lambda i: candidate_metrics[i]["distance_m"])
    b2 = min(range(len(candidate_metrics)), key=lambda i: candidate_metrics[i]["duration_s"])
    b3 = pick(SAFETY_WEIGHTS, "risk_static", "uncertainty_static")
    b4 = pick(SAFETY_WEIGHTS, "risk_dynamic", "uncertainty_dynamic")
    b5 = pick(UNCERTAINTY_AWARE_WEIGHTS, "risk_dynamic", "uncertainty_dynamic")

    def summary(idx: int, risk_key: str, unc_key: str) -> dict[str, float]:
        m = candidate_metrics[idx]
        return {
            "candidate": idx,
            "distance_m": m["distance_m"],
            "duration_s": m["duration_s"],
            "risk": m[risk_key],
            "uncertainty": m[unc_key],
            "safety": 1.0 - m[risk_key],
        }

    chosen = {
        "B1_shortest": summary(b1, "risk_dynamic", "uncertainty_dynamic"),
        "B2_fastest": summary(b2, "risk_dynamic", "uncertainty_dynamic"),
        "B3_static_safety": summary(b3, "risk_static", "uncertainty_static"),
        "B4_dynamic_safety": summary(b4, "risk_dynamic", "uncertainty_dynamic"),
        "B5_dynamic_uncertainty": summary(b5, "risk_dynamic", "uncertainty_dynamic"),
    }
    b4m, b1m, b2m = candidate_metrics[b4], candidate_metrics[b1], candidate_metrics[b2]
    comparisons = {
        "risk_reduction_pct_b4_vs_b1": (
            (b1m["risk_dynamic"] - b4m["risk_dynamic"]) / max(b1m["risk_dynamic"], 1e-9)
        )
        * 100,
        "time_penalty_pct_b4_vs_b2": ((b4m["duration_s"] - b2m["duration_s"]) / b2m["duration_s"])
        * 100,
        "distance_penalty_pct_b4_vs_b1": (
            (b4m["distance_m"] - b1m["distance_m"]) / b1m["distance_m"]
        )
        * 100,
    }
    return chosen, comparisons


def write_artifacts(result: dict[str, object]) -> tuple[Path, Path]:
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    json_path = ARTIFACTS / f"baselines-{ts}.json"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Baselines B1-B5 (recorded run)",
        "",
        f"- run_at: {result['run_at']}",
        f"- hour_ist: {result['hour_ist']}",
        f"- model_version: {result['model_version']}",
        f"- evidence_model_version: {result['evidence_model_version']}",
        "",
        "| pair | B1 m | B4 m | B1 risk | B4 risk | red. % | B2 s | B4 s | pen. % |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for p in result["pairs"]:  # type: ignore[union-attr]
        b1 = p["chosen"]["B1_shortest"]
        b2 = p["chosen"]["B2_fastest"]
        b4 = p["chosen"]["B4_dynamic_safety"]
        c = p["comparisons"]
        lines.append(
            f"| {p['pair']} | {b1['distance_m']:.1f} | {b4['distance_m']:.1f} | "
            f"{b1['risk']:.4f} | {b4['risk']:.4f} | "
            f"{c['risk_reduction_pct_b4_vs_b1']:+.1f}% | "
            f"{b2['duration_s']:.1f} | {b4['duration_s']:.1f} | "
            f"{c['time_penalty_pct_b4_vs_b2']:+.1f}% |"
        )
    agg = result["aggregates"]
    lines += [
        "",
        "## Aggregates",
        "",
        f"- mean risk reduction B4 vs B1: {agg['mean_risk_reduction_pct_b4_vs_b1']:+.1f}%",
        f"- mean time penalty B4 vs B2: {agg['mean_time_penalty_pct_b4_vs_b2']:+.1f}%",
        f"- mean distance penalty B4 vs B1: {agg['mean_distance_penalty_pct_b4_vs_b1']:+.1f}%",
    ]
    md_path = ARTIFACTS / f"baselines-{ts}.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


if __name__ == "__main__":
    result = run_baselines()
    json_path, md_path = write_artifacts(result)
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(json.dumps(result["aggregates"], indent=2))
