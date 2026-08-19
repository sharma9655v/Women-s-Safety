# Architecture (current state, 2026-08)

This document describes the system **as implemented**. The root-level
`architecture.md` / `api-spec.md` / `data-model.md` are the original plans;
where they differ, this file wins.

## High-level view

```
+----------------+      HTTPS       +-----------------------------------+
| apps/web       |  --------------->| apps/api (FastAPI, single process) |
| Next.js 16     |                 |  app/main.py                       |
| (Leaflet map)  |                 |  - routers under app/api/*         |
+----------------+                 |  - app/safety, app/evidence, ...   |
+----------------+      HTTPS       |  - app/cv (mock backend)          |
| android/app    |  --------------->|  - app/gis (city registry)        |
| Kotlin/Compose |                 |  - app/metrics (in-process)        |
+----------------+                 +-------+--------+--------+---------+
                                        |        |        |
                                 +------+        |        +------+
                                 | PostGIS      OSRM      Redis
                                 | (optional)   (local    (optional)
                                 |  fallback:   graph)
                                 |  in-memory
                                 +-------------+
```

## Runtime selection

- `DATABASE_URL` set → SQLAlchemy/PostGIS store (production).
- `DATABASE_URL` empty → in-memory store (dev/test). The store probe is
  memoized per process (`lru_cache`), so a down Postgres costs one
  ~10 s probe at startup and then runs on the fallback.
- `REDIS_URL` empty → in-process rate limiting. Set → Redis-backed.
- OSRM is required for `/api/routes` (error 503 is returned if unreachable).

## Components

| Component | Path | Responsibility |
| --- | --- | --- |
| API app | `apps/api/app/main.py` | routers, CORS, `/health`, `/ready`, `/metrics`, catch-all sanitized 500 handler |
| Routing | `apps/api/app/api/routes.py` + `app/safety/` | OSRM candidates → segment matching → deterministic risk scoring (3 profiles), rate-limited |
| Evidence | `apps/api/app/api/evidence.py` + `app/evidence/` | six-state lifecycle, append-only history, freshness decay, conflicts |
| Reports | `apps/api/app/api/reports.py` + `app/reports/` | anonymous pipeline: redact → dedupe → rate-limit → encrypt (Fernet) |
| Emergency/SOS | `apps/api/app/api/emergency.py` | countdown-gated sessions, one active per client, location updates, TTL |
| Guardian | `apps/api/app/api/guardian.py` | journeys, check-ins, deviation detection, escalation |
| Contacts | `apps/api/app/api/contacts.py` | per-client private contacts, phone encrypted at rest |
| Auth | `apps/api/app/api/auth.py` + `app/auth.py` | device-session tokens (30-day TTL, hashed at rest) |
| CV | `apps/api/app/cv/` + `app/api/cv.py` | model registry, health, predict; mock backend by default |
| Models | `apps/api/app/api/models.py` | active models + ML gate status + registry metadata |
| GIS | `apps/api/app/gis/` | city registry, city-level validation reports, fixtures |
| Metrics | `apps/api/app/metrics.py` | in-process Prometheus-style counters (request, ingest, CV, model) |
| Ingest | `apps/api/app/ingest_feed.py`, `app/osm_feed.py` | civic data feed validation/ingestion into PostGIS |
| Civic | `apps/api/app/civic/` | curated open data (streetlights, police stations, etc.) |

## Key rules (enforced, not aspirational)

1. Backend owns safety decisions; frontends only render them.
2. Routes carry risk probability, confidence, uncertainty, warnings,
   reasons, model version — never a bare "safe" claim.
3. ML stays out of the routing path until the gate opens (see
   `ml/ml/gate.py`): ≥1,000 **verified** observations over ≥90 days.
   `demo_seed` observations never count.
4. Reporters are never identified; descriptions are redacted; images
   stripped of EXIF and encrypted at rest.
5. The CV mock is explicitly labelled (`is_real_inference=false`); nothing
   ever claims real ML inference while the mock is active.
6. Metrics never log query strings (PII-safe).
