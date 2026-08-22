"""Multi-city validation pipeline.

Validates the evidence + GIS layers per city and produces a cross-city
report. Runs against the live stores (PostGIS / memory) and never fabricates
observations: when a store has no data for a city, the report says so
explicitly (missing-data detection), and the --fixture mode generates
deterministically-labelled synthetic fixtures for tests only.

Checks per city:
  - observation counts (total / per source class, demo vs real)
  - coordinate validity (bounds) and coverage (within city bbox)
  - duplicate-rate detection (evidence_hash collisions)
  - spatial consistency (observations on segments inside the city bbox)
  - date range of evidence
  - risk-layer generation (deterministic per-segment risk summary)
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from app.evidence.engine import Observation, SegmentEvidence, aggregate, evidence_hash
from app.evidence.store import EvidenceStore, MemoryEvidenceStore
from app.gis.cities import City, covers_coords, get_city, list_cities
from app.risk import SegmentRisk, compute_segment_risk
from app.segments.matcher import RoadSegment
from app.segments.store import MemorySegmentStore, SegmentStore


@dataclass
class CityStats:
    city: str
    observations: int = 0
    demo_observations: int = 0
    real_observations: int = 0
    fixture_observations: int = 0
    segments_with_evidence: int = 0
    segments_in_city: int = 0
    coverage_fraction: float = 0.0
    invalid_coordinate_rows: int = 0
    outside_bbox_rows: int = 0
    duplicate_hash_rows: int = 0
    min_observed_at: str | None = None
    max_observed_at: str | None = None
    observation_types: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    sources: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    mean_risk: float | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class CityValidationReport:
    generated_at: str
    cities: list[CityStats] = field(default_factory=list)
    total_observations: int = 0
    total_valid_observations: int = 0
    total_invalid_observations: int = 0
    total_duplicate_observations: int = 0
    fixture_mode: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "fixture_mode": self.fixture_mode,
            "total_observations": self.total_observations,
            "total_valid_observations": self.total_valid_observations,
            "total_invalid_observations": self.total_invalid_observations,
            "total_duplicate_observations": self.total_duplicate_observations,
            "cities": [c.to_dict() for c in self.cities],
        }


def _segment_observations(
    evidence: EvidenceStore, segment_ids: list[int]
) -> dict[int, list[Observation]]:
    grouped = evidence.observations_for_segments(segment_ids)
    return {seg_id: list(items) for seg_id, items in grouped.items()}


def validate_city(
    city: City,
    segments: SegmentStore,
    evidence: EvidenceStore,
    hour_ist: int = 12,
) -> CityStats:
    """Validate one city against the live stores."""
    south, west, north, east = city.bbox
    city_segments = list(segments.within_bbox(west, south, east, north))
    stats = CityStats(city=city.name, segments_in_city=len(city_segments))

    if not city_segments:
        stats.notes.append("no road segments available for this city in the current graph")
        return stats

    segment_ids = [seg.id for seg in city_segments]
    observations_by_segment = _segment_observations(evidence, segment_ids)
    covered = 0
    risks: list[float] = []
    seen_hashes: set[str] = set()
    dates: list[datetime] = []

    for seg in city_segments:
        observations = observations_by_segment.get(seg.id, [])
        if observations:
            covered += 1
        for obs in observations:
            stats.observations += 1
            if obs.source_type == "demo_seed":
                stats.demo_observations += 1
            elif obs.source_type == "fixture":
                stats.fixture_observations += 1
            else:
                stats.real_observations += 1
            stats.observation_types[obs.observation_type] += 1
            stats.sources[obs.source_type] += 1
            obs_hash = evidence_hash(
                obs.segment_id,
                obs.source_type,
                obs.observation_type,
                obs.value,
                obs.observed_at,
            )
            if obs_hash in seen_hashes:
                stats.duplicate_hash_rows += 1
            seen_hashes.add(obs_hash)
            dates.append(obs.observed_at)
            lat = obs.value.get("lat")
            lon = obs.value.get("lon")
            if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                continue  # most observations carry no explicit coordinate (segment-anchored)
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                stats.invalid_coordinate_rows += 1
            elif not covers_coords(city, float(lat), float(lon)):
                stats.outside_bbox_rows += 1

        if observations:
            evidence_summary: SegmentEvidence | None = aggregate(seg.id, observations)
            risk: SegmentRisk = compute_segment_risk(
                segment_id=seg.id,
                evidence=evidence_summary,
                road_type=seg.road_type,
                lit=seg.lit,
                nearest_emergency_m=None,
                hour_ist=hour_ist,
            )
            risks.append(risk.risk_probability)

    stats.segments_with_evidence = covered
    stats.coverage_fraction = covered / len(city_segments) if city_segments else 0.0
    if risks:
        stats.mean_risk = sum(risks) / len(risks)
    if dates:
        stats.min_observed_at = min(dates).isoformat(timespec="seconds")
        stats.max_observed_at = max(dates).isoformat(timespec="seconds")
    return stats


def run_validation(
    segments: SegmentStore,
    evidence: EvidenceStore,
    cities: list[City] | None = None,
    hour_ist: int = 12,
) -> CityValidationReport:
    """Run per-city validation and aggregate cross-city statistics."""
    cities = cities or list_cities()
    report = CityValidationReport(generated_at=datetime.now(UTC).isoformat(timespec="seconds"))
    for city in cities:
        stats = validate_city(city, segments, evidence, hour_ist=hour_ist)
        report.cities.append(stats)
        report.total_observations += stats.observations
        report.total_valid_observations += stats.real_observations
        report.total_invalid_observations += stats.invalid_coordinate_rows
        report.total_duplicate_observations += stats.duplicate_hash_rows
    return report


def build_fixture(city: City) -> tuple[MemorySegmentStore, MemoryEvidenceStore]:
    """Deterministic SYNTHETIC fixture for one city (tests only).

    The synthetic segments/observations are labelled source_type='fixture'
    so they can never be confused with real evidence; this function exists
    solely so the validation pipeline is testable without a live database.
    """
    from datetime import timedelta

    from app.evidence.engine import Observation
    from app.evidence.states import VerificationState

    segments: list[RoadSegment] = []
    observations: list[Observation] = []
    south, west, north, east = city.bbox
    for i in range(200):
        # Deterministic pseudo-random placement inside the bbox.
        fraction = (i * 37) % 1000 / 1000.0
        lat = south + (north - south) * fraction
        lon = west + (east - west) * ((i * 53) % 1000 / 1000.0)
        segments.append(
            RoadSegment(
                id=100_000 + i,
                geometry=((lon, lat), (lon + 0.001, lat + 0.0005)),
                road_type="residential" if i % 2 else "footway",
                lit="yes" if i % 3 else "no",
            )
        )
        if i % 3 == 0:
            observed_at = datetime(2026, 8, 1, 12, 0, tzinfo=UTC) + timedelta(hours=i)
            observations.append(
                Observation(
                    segment_id=100_000 + i,
                    source_type="fixture",
                    observation_type="poor_lighting",
                    observed_at=observed_at,
                    source_reliability=0.5,
                    value={"poor": True},
                    state=VerificationState.REPORTED,
                )
            )
    return MemorySegmentStore(segments), MemoryEvidenceStore(observations)


def write_report(report: CityValidationReport, path: str | None = None) -> str:
    """Persist the report as JSON (data/versions-style artifact)."""
    from pathlib import Path

    out = (
        Path(path)
        if path
        else (
            Path(__file__).resolve().parents[4]
            / "data"
            / "versions"
            / f"city-validation-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}.json"
        )
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return str(out)


def render_table(report: CityValidationReport) -> str:
    """Human-readable markdown table (used by the CLI and docs)."""
    lines = [
        "| City | Segments | Observations | Real | Demo | Coverage | Invalid | "
        "Duplicates | Mean risk |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for stats in report.cities:
        mean_risk = f"{stats.mean_risk:.4f}" if stats.mean_risk is not None else "—"
        lines.append(
            f"| {stats.city} | {stats.segments_in_city} | {stats.observations} | "
            f"{stats.real_observations} | {stats.demo_observations} | "
            f"{stats.coverage_fraction:.2%} | {stats.invalid_coordinate_rows} | "
            f"{stats.duplicate_hash_rows} | {mean_risk} |"
        )
    return "\n".join(lines)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate evidence + GIS coverage per city (multi-city pipeline)."
    )
    parser.add_argument("--city", default=None, help="validate a single city (default: all)")
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="use deterministic SYNTHETIC fixtures instead of live stores",
    )
    parser.add_argument("--hour-ist", type=int, default=12, help="hour_ist for risk scoring")
    parser.add_argument("--out", default=None, help="write the JSON report to this path")
    args = parser.parse_args()

    cities = [get_city(args.city)] if args.city else list_cities()
    if args.fixture:
        from app.gis.validation import build_fixture

        segments_stores = []
        evidence_stores = []
        for city in cities:
            segs, evs = build_fixture(city)
            segments_stores.append(segs)
            evidence_stores.append(evs)
        # Merge fixture stores across cities (synthetic ids are unique per city).
        all_segments = [seg for store in segments_stores for seg in store.all()]
        all_obs = [obs for store in evidence_stores for obs in store._observations]
        segments = MemorySegmentStore(all_segments)
        evidence = MemoryEvidenceStore(all_obs)
        report = run_validation(segments, evidence, cities=cities, hour_ist=args.hour_ist)
        report.fixture_mode = True
    else:
        from app.evidence.registry import get_evidence_store
        from app.segments.registry import get_segments_store

        report = run_validation(
            get_segments_store(), get_evidence_store(), cities=cities, hour_ist=args.hour_ist
        )

    print(render_table(report))
    out_path = write_report(report, args.out)
    print(f"report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
