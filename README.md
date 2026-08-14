# Map for Women — Vibe Coding Project

## Product
Map for Women is a safety-aware navigation platform for women. It does NOT guarantee safety. It estimates route risk using time-aware, heterogeneous evidence and returns Safety Priority, Balanced, and Time Priority routes.

## Research contribution
Safest-route navigation already exists in products and research. The proposed contribution is:
Dynamic + uncertainty-aware + freshness-aware + explainable safety routing under incomplete, stale and conflicting urban data.

## MVP
- Next.js/React + TypeScript
- Leaflet + OpenStreetMap
- OSRM routing
- FastAPI
- PostgreSQL + PostGIS
- Evidence/freshness/confidence engine
- Deterministic safety baseline first
- XGBoost only after real labeled data exists
- Anonymous safety reports
- Explainable route cards

## Rule
Build the deterministic GIS/routing pipeline first. Never invent ML accuracy or safety scores.

## Repository layout

```
apps/api    FastAPI backend (uv) — safety decisions live here
apps/web    Next.js frontend (pnpm) — renders what the backend decides
infra       Docker Compose: postgis, redis, osrm, api, web
data        OSM extracts, loaders, version manifests (gitignored artifacts)
ml          Experiments + versioned model artifacts (Phase 6)
docs        Additional design/ops notes
```

## Quickstart

Prereqs: Node 20.9+, pnpm, uv, Docker with Compose.

```bash
cp .env.example .env        # local defaults are fine for dev
pnpm install                # web deps

# Local (no Docker)
pnpm dev:api                # http://localhost:8000  (/health)
pnpm dev:web                # http://localhost:3000

# Full stack (Docker)
docker compose -f infra/compose.yaml up --build
```

The OSRM service bootstraps with the small Delhi extract by default. For the
India-wide graph set `OSM_PBF_URL=https://download.geofabrik.de/asia/india-latest.osm.pbf`
in `infra/compose.yaml`.

## Definition of done
API validation + errors + tests + privacy review + traceable model/data version + uncertainty-aware UI. Details in implementation-plan.md.
