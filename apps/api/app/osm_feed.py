"""Fetch real OSM data for the Delhi area and emit a validated feed.

The only real, licence-clear data source that maps 1:1 onto the routing graph
today is OpenStreetMap (ODbL). This script queries the public Overpass API for
routable ways in the Delhi bounding box carrying explicit attribute tags, and
maps them onto the evidence vocabulary:

  - highway + lit=no              -> poor_lighting      {"poor": true}
  - highway + sidewalk=no|none    -> blocked_sidewalk   {"blocked": true}
  - highway + surface (unpaved..) -> road_hazard        {"hazard": true, "kind": ...}

Honesty rules:
  - observed_at is the FETCH DATE (today): these are "state as currently
    mapped" observations, not edit-date claims.
  - verification_state is REPORTED, never VERIFIED: OSM is crowd-sourced; the
    admin Review Queue verifies before the rows count toward the ML gate.
  - source_reliability 0.7 (crowd-sourced, machine-verifiable attribute tags).
  - source_type 'osm' is real data and is NOT the demo source; the harness
    still requires an explicit --write to touch PostGIS.

Usage:
    uv run --directory apps/api python -m app.osm_feed                # fetch + dry run
    uv run --directory apps/api python -m app.osm_feed --write        # fetch + insert
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from app.ingest_feed import run_ingest

# NCT Delhi approximate bounding box.
DELHI_BBOX = (28.35, 76.75, 28.95, 77.40)

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

UNPAVED_SURFACES = ("unpaved", "gravel", "ground", "dirt", "sand", "mud", "grass")

QUERY = """\
[out:json][timeout:180][maxsize:1073741824];
(
  way({s},{w},{n},{e})["highway"]["lit"="no"];
  way({s},{w},{n},{e})["highway"]["sidewalk"~"^(no|none)$"];
  way({s},{w},{n},{e})["highway"]["surface"~"^({surfaces})$"];
);
out tags;
"""


def fetch_osm(south: float, west: float, north: float, east: float) -> list[dict[str, Any]]:
    """Query Overpass (with mirror fallback). Returns element dicts."""
    query = QUERY.format(
        s=south,
        w=west,
        n=north,
        e=east,
        surfaces="|".join(UNPAVED_SURFACES),
    )
    body = urllib.parse.urlencode({"data": query}).encode("utf-8")
    last_error: Exception | None = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            request = urllib.request.Request(
                endpoint,
                data=body,
                method="POST",
                headers={
                    "User-Agent": "women-safety-pipeline/1.0 (validated feed fetch; ODbL)",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if "elements" not in payload:
                raise ValueError(f"unexpected Overpass response from {endpoint}")
            return cast(list[dict[str, Any]], payload["elements"])
        except Exception as exc:  # network failure or malformed response
            last_error = exc
            time.sleep(2)
    raise RuntimeError(f"all Overpass endpoints failed: {last_error}")


def map_elements_to_rows(
    elements: list[dict[str, Any]],
    observed_at: datetime,
    segment_map: dict[int, list[int]],
) -> tuple[list[dict[str, object]], int]:
    """Map OSM way tags to harness feed rows, one row per GRAPH segment
    (road_segments.id, resolved through osm_way_id). Ways absent from the
    routing graph are skipped and counted — evidence on non-graph ways never
    reaches routing, so it must not be stored."""
    rows: list[dict[str, object]] = []
    skipped = 0
    for element in elements:
        if element.get("type") != "way":
            continue
        way_id = element.get("id")
        tags = element.get("tags", {})
        if not isinstance(way_id, int) or not isinstance(tags, dict):
            continue
        highway = tags.get("highway")
        if not highway:
            continue
        segment_ids = segment_map.get(way_id, [])
        if not segment_ids:
            skipped += 1
            continue
        surface = tags.get("surface")
        for segment_id in segment_ids:
            if tags.get("lit") == "no":
                rows.append(_row(segment_id, "poor_lighting", {"poor": True}, observed_at))
            if tags.get("sidewalk") in ("no", "none"):
                rows.append(_row(segment_id, "blocked_sidewalk", {"blocked": True}, observed_at))
            if surface in UNPAVED_SURFACES:
                rows.append(
                    _row(segment_id, "road_hazard", {"hazard": True, "kind": surface}, observed_at)
                )
    return rows, skipped


def _row(
    segment_id: int, observation_type: str, value: dict[str, bool | str], observed_at: datetime
) -> dict[str, object]:
    return {
        "segment_id": segment_id,
        "observation_type": observation_type,
        "value_json": value,
        "observed_at": observed_at.isoformat(timespec="seconds"),
        "source_reliability": 0.7,
        "verification_state": "REPORTED",
    }


def load_way_segment_map(way_ids: set[int]) -> dict[int, list[int]]:
    """Resolve OSM way ids to routing-graph segment ids (road_segments.id via
    osm_way_id). Requires PostGIS — without the graph, segment ids cannot be
    known, so the fetch fails honestly instead of emitting wrong ids."""
    from sqlalchemy import text

    from app.db import make_engine

    engine = make_engine()
    mapping: dict[int, list[int]] = {}
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        result = conn.execute(
            text("SELECT id, osm_way_id FROM road_segments WHERE osm_way_id = ANY(:ids)"),
            {"ids": sorted(way_ids)},
        )
        for segment_id, osm_way_id in result:
            mapping.setdefault(int(osm_way_id), []).append(int(segment_id))
    return mapping


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Delhi OSM data as a validated feed.")
    parser.add_argument("--write", action="store_true", help="insert into PostGIS after validation")
    parser.add_argument(
        "--out", type=Path, default=None, help="feed CSV path (default: repo data/)"
    )
    args = parser.parse_args()

    observed_at = datetime.now(UTC).replace(microsecond=0)
    print(f"Fetching Delhi OSM from Overpass ({observed_at.isoformat()}) ...")
    elements = fetch_osm(*DELHI_BBOX)
    way_ids = {
        int(e["id"]) for e in elements if e.get("type") == "way" and isinstance(e.get("id"), int)
    }
    print(f"Fetched {len(elements)} ways; resolving {len(way_ids)} to graph segments ...")
    segment_map = load_way_segment_map(way_ids)
    rows, skipped = map_elements_to_rows(elements, observed_at, segment_map)
    print(
        f"Mapped {len(rows)} observations across {len(segment_map)} graph segments; "
        f"{skipped} ways not in the routing graph (skipped)."
    )

    out_path = args.out or (Path(__file__).resolve().parents[1] / "data" / "osm-feed.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]) if rows else [], extrasaction="ignore"
        )
        if rows:
            writer.writeheader()
            for row in rows:
                row["value_json"] = json.dumps(row["value_json"], sort_keys=True)
            writer.writerows(rows)

    result = run_ingest(
        out_path,
        "osm",
        "ODbL 1.0",
        drop_columns=True,
        write=args.write,
        out_dir=Path(__file__).resolve().parents[3] / "data" / "versions",
    )
    print(json.dumps(result, indent=1))
    return 0 if "error" not in result else 3


if __name__ == "__main__":
    raise SystemExit(main())
