# One-command demo

Starts the full stack (PostGIS, Redis, OSRM, API, web), seeds deterministic
demo evidence (labeled `demo_seed`, never treated as real), and prints URLs.

## Requirements

- Docker Desktop running
- `uv` installed (Python 3.13)
- `.env` at the repo root with `DATABASE_URL` pointing at `localhost:5432`

## Usage

From PowerShell, in `infra/`:

```powershell
./demo.ps1
```

Then open:

- Web app: http://localhost:3000 (starts on `/live`)
- API docs: http://localhost:8000/docs

## What it does

1. `docker compose up -d --build postgis redis osrm`
2. Waits for PostGIS to accept connections
3. Runs `uv run python -m app.seed_demo` (deterministic and idempotent —
   observations are keyed by evidence_hash anchored to the current hour, so
   re-runs within the same hour dedupe; writes
   `data/processed/demo-evidence.json` + a versioned manifest in `data/versions/`)
4. `docker compose up -d --build api web`

## Demo tips

- The map shows seeded incident + streetlight markers; the "Demo data" badge
  appears when any overlay source is `demo_seed`.
- In the route planner, "Demo: simulate time → Night" replans with `hour_ist=22`
  so night-time risk drives route choice (scores change vs. "Now").
- The API falls back to the snapshot in memory if PostGIS is unreachable
  (`EVIDENCE_SEED_JSON` is mounted into the api container read-only).
- `docker compose down` stops everything; volumes (PostGIS data, OSRM graph)
  are preserved.