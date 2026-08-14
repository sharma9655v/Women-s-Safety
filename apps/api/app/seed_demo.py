"""Seed demo evidence for the SIH demo (deterministic, idempotent, labeled).

Every observation is written with source_type='demo_seed' so the UI can show
a "Demo data" badge, the ML gate never counts it, and the API can prove it is
illustrative, not real. Re-running this script is safe: observations are keyed
by a canonical evidence_hash (ON CONFLICT DO NOTHING).

Usage:
    uv run python -m app.seed_demo [--snapshot-only]

Exit codes: 0 ok, 2 cannot reach PostGIS (and not --snapshot-only).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, text

from app.config import settings
from app.evidence.engine import evidence_hash

REPO_ROOT = Path(__file__).resolve().parents[3]

DEMO_SOURCE = "demo_seed"
DEMO_RELIABILITY = 0.55

HOTSPOTS = [
    ("Connaught Place", 28.6315, 77.2167),
    ("India Gate", 28.6129, 77.2295),
    ("Chandni Chowk", 28.6500, 77.2310),
    ("Hauz Khas Village", 28.5494, 77.2001),
    ("Karol Bagh", 28.6515, 77.1908),
    ("Lajpat Nagar", 28.5677, 77.2433),
    ("Saket", 28.5245, 77.2066),
    ("Delhi University North Campus", 28.6900, 77.2060),
    ("Paharganj", 28.6450, 77.2100),
    ("Dwarka Sector 21", 28.5563, 77.0579),
]

# (observation_type, value, fresh_count, aging_count, stale_count)
INCIDENT_PLAN = [
    ("harassment", {"incident": True}, 3, 4, 3),
    ("suspicious_activity", {"incident": True}, 2, 3, 2),
    ("road_hazard", {"incident": True, "hazard": True}, 1, 2, 1),
]

LIGHTING_PLAN = [
    ("streetlight_not_working", {"working": False}, 3, 3, 2),
    ("poor_lighting", {"poor": True}, 2, 2, 1),
]

FRESH_DAYS = 2
AGING_DAYS = 5
STALE_DAYS = 34


def _pick_segments(engine, lat: float, lon: float, radius_m: int, k: int) -> list[dict]:
    stmt = text(
        "SELECT id, road_type, lit, "
        "ST_Y(ST_LineInterpolatePoint(geometry, 0.5)) AS lat, "
        "ST_X(ST_LineInterpolatePoint(geometry, 0.5)) AS lon "
        "FROM road_segments "
        "WHERE ST_DistanceSphere(geometry, ST_MakePoint(:lon, :lat)) < :radius "
        "ORDER BY id LIMIT :k"
    )
    with engine.connect() as conn:
        rows = conn.execute(
            stmt,
            {"lat": lat, "lon": lon, "radius": radius_m, "k": k},
        ).fetchall()
    return [
        {
            "segment_id": int(row.id),
            "lat": float(row.lat),
            "lon": float(row.lon),
            "area_name": "",
        }
        for row in rows
    ]


def _build_observation(
    segment_id: int,
    source_type: str,
    observation_type: str,
    value: dict[str, bool],
    observed_at: datetime,
    verification_state: str,
) -> dict[str, object]:
    return {
        "segment_id": segment_id,
        "source_type": source_type,
        "observation_type": observation_type,
        "value_json": json.dumps(value, sort_keys=True),
        "observed_at": observed_at,
        "source_reliability": DEMO_RELIABILITY,
        "confidence": 0.5,
        "verification_state": verification_state,
        "evidence_hash": evidence_hash(
            segment_id, source_type, observation_type, value, observed_at
        ),
    }


def _row_to_snapshot_item(
    row: object, lat: float, lon: float, area_name: str
) -> dict[str, object]:
    value_json = row.value_json  # type: ignore[attr-defined]
    if not isinstance(value_json, dict):
        value_json = {}
    working = value_json.get("working")
    return {
        "observation_id": row.id,  # type: ignore[attr-defined]
        "segment_id": row.segment_id,  # type: ignore[attr-defined]
        "observation_type": row.observation_type,  # type: ignore[attr-defined]
        "source_type": row.source_type,  # type: ignore[attr-defined]
        "observed_at": row.observed_at.isoformat(),  # type: ignore[attr-defined]
        "verification_state": row.verification_state,  # type: ignore[attr-defined]
        "working": working,
        "lat": lat,
        "lon": lon,
        "area_name": area_name,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-only", action="store_true")
    parser.add_argument("--segments-per-spot", type=int, default=26)
    args = parser.parse_args()

    rng = random.Random(20260814)
    # Anchor to the top of the current hour so re-running within the same hour
    # produces identical evidence_hashes (ON CONFLICT DO NOTHING) and is fully
    # idempotent, while fresh/aging/stale tiers still reflect real time.
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    engine = create_engine(settings.database_url)

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        if args.snapshot_only:
            print(f"PostGIS unreachable ({exc}); skipping DB insert.")
            engine = None
        else:
            print(f"ERROR: PostGIS unreachable: {exc}")
            return 2

    total = 0
    snapshot_items: list[dict[str, object]] = []
    if engine is not None:
        with engine.begin() as conn:
            for name, lat, lon in HOTSPOTS:
                segments = _pick_segments(engine, lat, lon, 900, args.segments_per_spot)
                for seg in segments:
                    seg["area_name"] = name
                obs_rows: list[dict[str, object]] = []
                for obs_type, value, fresh, aging, stale in INCIDENT_PLAN + LIGHTING_PLAN:
                    sample_size = min(fresh + aging + stale, len(segments))
                    for seg in rng.sample(segments, sample_size):
                        age_days = rng.choice([FRESH_DAYS, AGING_DAYS, STALE_DAYS])
                        observed_at = now - timedelta(days=age_days)
                        roll = rng.random()
                        if roll < 0.12:
                            state = "VERIFIED"
                        elif roll < 0.16:
                            state = "CONFLICTING"
                        else:
                            state = "REPORTED"
                        obs_rows.append(
                            _build_observation(
                                seg["segment_id"],
                                DEMO_SOURCE,
                                obs_type,
                                value,
                                observed_at,
                                state,
                            )
                        )
                for row in obs_rows:
                    conn.execute(
                        text(
                            "INSERT INTO safety_observations "
                            "(segment_id, source_type, observation_type, value_json, observed_at, "
                            "source_reliability, confidence, verification_state, evidence_hash) "
                            "VALUES (:segment_id, :source_type, :observation_type, :value_json, "
                            ":observed_at, :source_reliability, :confidence, :verification_state, "
                            ":evidence_hash) ON CONFLICT (evidence_hash) DO NOTHING"
                        ),
                        row,
                    )
                total += len(obs_rows)

        with engine.connect() as conn:
            for name, lat, lon in HOTSPOTS:
                rows = conn.execute(
                    text(
                        "SELECT o.id, o.segment_id, o.observation_type, o.source_type, "
                        "o.observed_at, o.verification_state, o.value_json, "
                        "ST_Y(ST_LineInterpolatePoint(s.geometry, 0.5)) AS lat, "
                        "ST_X(ST_LineInterpolatePoint(s.geometry, 0.5)) AS lon "
                        "FROM safety_observations o JOIN road_segments s ON s.id = o.segment_id "
                        "WHERE o.source_type = :src AND "
                        "ST_DistanceSphere(s.geometry, ST_MakePoint(:lon, :lat)) < 1000"
                    ),
                    {"src": DEMO_SOURCE, "lat": lat, "lon": lon},
                ).fetchall()
                for row in rows:
                    snapshot_items.append(
                        _row_to_snapshot_item(row, float(row.lat), float(row.lon), name)
                    )

    snapshot = {
        "description": (
            "Illustrative demo evidence for SIH demos. source_type=demo_seed; "
            "never counts toward the ML gate; the UI labels it as demo data."
        ),
        "generated_at": now.isoformat(),
        "count": len(snapshot_items),
        "observations": snapshot_items,
    }
    snapshot_path = REPO_ROOT / "data" / "processed" / "demo-evidence.json"
    with open(snapshot_path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=1)

    manifest = {
        "name": "demo-evidence",
        "generated_at": now.isoformat(),
        "observation_count": len(snapshot_items),
        "inserted_or_kept": total,
        "source_type": DEMO_SOURCE,
        "hotspots": [h[0] for h in HOTSPOTS],
        "sha256": hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest(),
    }
    manifest_path = REPO_ROOT / "data" / "versions" / f"demo-evidence-{now:%Y%m%dT%H%M%S}.json"
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)

    print(f"seeded {len(snapshot_items)} demo observations ({total} inserts attempted)")
    print(f"snapshot: {snapshot_path}")
    print(f"manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
