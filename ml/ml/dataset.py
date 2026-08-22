"""Versioned dataset snapshot for training-time experiments.

Exports the evidence table with the exact features a baseline model would
consume, plus the label of record (verification_state). Snapshots are
immutable: a new run writes a new dataset_version, never overwriting.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

import psycopg

DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/mapforwomen"

EXPORT_SQL = """
SELECT
    o.id,
    o.segment_id,
    o.source_type,
    o.observation_type,
    o.verification_state,
    o.confidence,
    o.source_reliability,
    o.observed_at,
    o.expires_at,
    s.road_type,
    s.lit
FROM safety_observations o
LEFT JOIN road_segments s ON s.id = o.segment_id
ORDER BY o.observed_at
"""


def export_dataset(
    database_url: str = DATABASE_URL,
    out_dir: Path | None = None,
) -> dict[str, object]:
    dataset_version = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    out_dir = out_dir or Path(__file__).parent / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"dataset-{dataset_version}.csv"
    rows: list[dict[str, object]] = []
    with psycopg.connect(database_url.replace("+psycopg", "")) as conn:
        with conn.cursor() as cur:
            cur.execute(EXPORT_SQL)
            for row in cur.fetchall():
                rows.append(
                    {
                        "id": row[0],
                        "segment_id": row[1],
                        "source_type": row[2],
                        "observation_type": row[3],
                        "verification_state": row[4],
                        "confidence": row[5],
                        "source_reliability": row[6],
                        "observed_at": row[7].isoformat() if row[7] else None,
                        "expires_at": row[8].isoformat() if row[8] else None,
                        "road_type": row[9],
                        "lit": row[10],
                    }
                )
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    manifest = {
        "dataset_version": dataset_version,
        "file": csv_path.name,
        "rows": len(rows),
        "span": {
            "min_observed_at": rows[0]["observed_at"] if rows else None,
            "max_observed_at": rows[-1]["observed_at"] if rows else None,
        },
        "verified_count": sum(1 for r in rows if r["verification_state"] == "VERIFIED"),
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    manifest_path = out_dir / f"dataset-{dataset_version}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
