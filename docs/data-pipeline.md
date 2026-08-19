# Data pipeline

How civic and safety data gets into the system — honestly, with versions
and provenance.

## Sources

| Source | Script | Output |
| --- | --- | --- |
| Civic open data (streetlights, police stations, hospitals, transit, etc.) | `apps/api/app/civic/` (curated) + `apps/api/app/ingest_feed.py` | PostGIS tables |
| OpenStreetMap (OSM) Overpass API | `apps/api/app/osm_feed.py` | `data/osm-feed-{city}.csv` |
| Crowd reports | `POST /api/reports` | in-memory / PostGIS with redaction + dedupe + encryption |
| ML training observations | `ml/ml/gate.py` + seed scripts | `ml/data/` (versioned) |
| Synthetic validation fixtures | `app/gis/validation.py --fixture` | write-only fixture rows, source_type=`fixture`, never counted as real |

## `ingest_feed.py` (generic feed importer)

```text
usage: python -m app.ingest_feed <feed.csv|jsonl> --source <name> --licence <text>
       [--drop-columns] [--write] [--batch-size N]
```

- Validates rows against the observation schema (`_coerce`), rejects
  unknown columns unless `--drop-columns`.
- `--write` inserts into PostGIS with `ON CONFLICT DO NOTHING`
  (idempotent) and a retry wrapper: `WRITE_RETRIES=3`,
  `WRITE_RETRY_BACKOFF_S=1.0`.
- Every attempt records an ingest metric:
  `ingest_rows_validated`, `ingest_rows_written`,
  `ingest_db_unreachable`, `ingest_write_failed`, `ingest_empty_fetch`.
- Without `--write` it validates only (safe to run anywhere).

## `osm_feed.py` (Overpass → observations)

```text
usage: python -m app.osm_feed --city delhi [--write]
       python -m app.osm_feed --bbox south,west,north,east [--write]
```

- Multi-city: `--city` resolves through the GIS registry
  (`app/gis/cities.py`, 10 cities). `--bbox` overrides.
- Writes `data/osm-feed-{city}.csv` for inspection before `--write`.
- An empty fetch records `ingest_empty_fetch` instead of failing.

## Provenance rules

- Every observation carries `source_type` (e.g. `civic_open_data`,
  `osm`, `crowd`, `fixture`) and `observed_at`; the schema tracks
  who/what collected it (attribution) and licence.
- `fixture` observations are counted separately from real ones
  (`fixture_observations` vs `observations`) in validation reports and
  the ML gate; they can never push the gate open.
- Evidence history is append-only; verification state transitions are
  recorded (six-state lifecycle in `app/evidence/`).

## Validation reports

`python -m app.gis.validation --city delhi [--fixture N] [--hour-ist H] [--out data/versions/...]`

Writes a JSON report (`CityValidationReport`) per city with per-type and
per-source counters, freshness, and coverage stats to
`data/versions/city-validation-{city}-{date}.json` (repo root via
`parents[4]`), and renders a terminal table. A daily run is the intended
cron job; reports are versioned files, not overwritten.
