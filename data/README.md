# Data & Versioning

All datasets here are treated as immutable artifacts with recorded provenance.

## Data directory

- `data/india-latest.osm.pbf` — Geofabrik India extract (gitignored, large).
- `data/processed/` — derived tables/parquets (gitignored).
- `data/versions/` — version manifests describing what was ingested, when, and from where.

## Manifest format

Each ingest writes `data/versions/<dataset>-<YYYYMMDD>.json`:

```json
{
  "dataset": "osm-india",
  "source": "https://download.geofabrik.de/asia/india-latest.osm.pbf",
  "downloaded_at": "2026-08-13T10:00:00Z",
  "pbf_revision": "<sha256 of file>",
  "rows_loaded": 0,
  "notes": ""
}
```

## Rules

1. Never overwrite an older manifest.
2. Record the PBF revision (sha256) — a map that depends on an unversioned extract cannot be reproduced.
3. Models must reference the exact dataset version they were trained on (`data/versions/…`).
4. Evidence rows are append-only; history is never mutated.