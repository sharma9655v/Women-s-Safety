# Implementation Plan — Map for Women

Coding order per AGENTS.md: **deterministic map/routing → evidence engine → tests → reports → ML → research experiments.**

Definition of done per phase: API validation + errors + tests + privacy review + traceable model/data version + uncertainty-aware UI. Nothing here invents safety guarantees; all fallback behavior follows design.md failure states.

## Convention & Tooling
- Monorepo: `apps/web` (Next.js + TS + Leaflet, pnpm workspace), `apps/api` (FastAPI + SQLAlchemy + uv), `infra/` (Compose, OSRM build), `data/` (loaders, version manifests, PBF **gitignored**), `ml/` (experiments, versioned artifacts), `tests/`.
- Services via `infra/compose.yaml`: `postgis`, `redis`, `osrm` (custom image, walking profile), `api`, `web`.
- CI: ruff (api), biome/eslint + `tsc --noEmit` (web), `pytest` (api), prettier. `.env` from `.env.example`; secrets never committed.
- Data/model versioning: dataset manifests in `data/versions/`, versioned tables (`model_versions`, `evidence_hash`); never overwrite old versions.

## Phase 0 — Foundations ✅
- Git init, repo skeleton, `.gitignore`, `.env`, workspace config (`pnpm-workspace.yaml`, `pyproject.toml`).
- Compose up: PostGIS, Redis, OSRM image, API with `/health`, web.
- CI pipeline: lint + typecheck + tests green.
- **Acceptance:** `docker compose up` runs all services; CI passes; `GET /health` returns status.
- *Status: done 2026-08-13. Docker Compose config written but unverified (Docker not installed on dev machine at the time); verified end-to-end in Phase 2.*

## Phase 1 — Map & Routing UI ✅
- Leaflet map + OSM tiles; origin/destination pickers; mode (walking first) + safety preference selector.
- OSRM: build graph from India Geofabrik PBF (`data/india-latest.osm.pbf`), walking profile; record PBF revision in dataset manifest.
- `POST /api/routes` proxy to OSRM → 3 candidate routes.
- **Acceptance:** 3 candidates render; routing failure returns explicit error, never a fake route.
- *Status: done 2026-08-13. API: `POST /api/routes` (validation 422, OSRM errors 502, unreachable 503), OSRM client with profile map + 3 alternatives, 10 tests green. Web: click-to-set origin/destination, mode + priority selects, route list, explicit error banner. Data: `data/loaders/fetch-osm.ps1` + `data/versions/northern-zone-latest-20260813.json` (sha256 recorded). NOTE: Geofabrik has no Delhi extract; Northern Zone used as dev default.*

## Phase 2 — Segments & Facilities
- `osm2pgsql` → PostGIS `road_segments` (osm_way_id, geometry, road_type, lit, timestamps).
- Facilities (police, hospital, pharmacy, fire_station, transit_stop, public_place) via Overpass; `facilities` table.
- Map-match candidate routes to segment ids (PostGIS `ST_ClosestPoint`/intersection); upsert segments with lineage, keep history.
- **Acceptance:** route → ordered segment list; source/lineage recorded for every row.
- **Status: DONE (verified end-to-end).** Docker Desktop installed/started; PostGIS 16 + Redis + OSRM (foot graph, northern-zone extract) + api + web all running via compose. Loaded: 1,887,882 road segments (osm2pgsql 1.11 via Ubuntu container, roads-flex.lua) and 3,927 facilities (ogr2ogr GDAL container) into PostGIS, both stamped `dataset_version=20260813`; history trigger + GIST indexes live. `PostgisSegmentStore` implemented and verified (incl. bbox query for fast matching). E2E: containerized API + real OSRM + PostGIS returns 3 real walking routes with ordered segment_ids (427/539/470 segments). Fixes found during verification: OSRM Dockerfile pinned to v5.25.0 (v5.27.1 has no published image), init-osrm.sh prefix/path bugs, Lua require-shim for osm2pgsql 1.x/2.x, facilities `dataset_version` default, uv:0.11 builder image has no shell, osm2pgsql `--flex` flag dropped in 2.x.

## Phase 3 — Evidence Engine
- Tables per data-model.md: `safety_observations`, `safety_reports`, `data_sources`; source-reliability tiers.
- Freshness per type: `freshness = exp(-lambda * age)` with per-type lambdas (not one universal rate).
- State machine: VERIFIED / REPORTED / CORROBORATED / CONFLICTING / EXPIRED / REJECTED; append-only history with `evidence_hash`.
- Per-segment aggregation: counts, recency-weighted score, conflict detection, confidence.
- **Unit tests** for decay, aggregation, conflicts, expiry, history immutability.
- **Acceptance:** `GET /api/segments/{id}/evidence` returns freshness, confidence, source counts, conflicts — never reporter identity.
- **Status: DONE (verified end-to-end).** `app/evidence/` (states, freshness, engine, store, registry) + `app/api/evidence.py` + schemas/models/schema.sql (data_sources seeded with 5 reliability tiers; safety_observations with UNIQUE evidence_hash + append-only safety_observation_history trigger; safety_reports). State machine: REJECTED/VERIFIED immutable; expiry per type; boolean conflicts (working/poor/blocked) → CONFLICTING; corroboration on ≥2 distinct source types or ≥3 items (independence proxy — reporter identity never stored); freshness clamps to 0 at expiry point. Score = Σ freshness×reliability; confidence = 1−exp(−2·score) capped 0.95, ×0.5 on conflict. API suite 47 tests green (ruff/mypy/format clean). Live: schema applied to PostGIS, 6 observations seeded (harassment×2 → REPORTED, streetlight user+city_data → CORROBORATED, expired poor_lighting excluded), history trigger wrote 6 rows, `GET /api/segments/456736/evidence` returns per-type summaries, 404 for unknown segments, no identity fields.

## Phase 4 — Deterministic Baseline (risk + routing)
- Rule-based risk model (design.md features): incident count/recency, lighting evidence + confidence, facility distance, road type, time/day.
- Uncertainty from evidence coverage/conflict; sparse data → "Limited safety data" + low confidence.
- Routing cost: `C = alpha*distance + beta*time + gamma*risk + delta*uncertainty`; safety preference reweights alpha/gamma/delta.
- Output 3 ranked routes: Safety Priority / Balanced / Time Priority; explanation_json per route; response conforms to api-spec.md — never `safe=true`, always model_version (`deterministic-baseline-v1`).
- **Acceptance:** end-to-end `POST /api/routes` returns 3 explainable, uncertainty-aware routes; deterministic round-trip tests green.
- **Status: DONE (verified end-to-end).** `app/risk/` (model, routing) + `app/facilities/` store (memory/PostGIS, bbox queries). Deterministic per-segment risk: incident score (harassment/suspicious_activity), lighting evidence + OSM lit tag, emergency-facility logistic distance (police/hospital/fire_station), road-type night risk (footway/path/steps...), time/day (IST night 20:00–04:59 ×1.35); confidence from evidence coverage, ×0.7 on conflict, capped 0.95; sparse data → "Limited safety data" + 0.25 confidence. Routing: `C = a·distance + b·time + g·risk + d·uncertainty` with risk@4 km-equivalent and uncertainty@400 m-equivalent so risk really differentiates profiles (safety γ=2.0 / balanced / time γ=0.3); labels = argmin per profile; length-weighted route aggregates via haversine; warnings for sparse (>50%) and conflicts. API: 3 labeled routes (safety_priority/balanced/time_priority) with risk_probability, estimated_safety (0–100, never `safe=true`), confidence, uncertainty, reasons, warnings, model_version `deterministic-baseline-v1`, segment_ids. Batch evidence (`observations_for_segments`, single ANY-query) + single union-bbox segment query for match+features — no full-table scans. API suite 65 tests green (ruff/mypy/format clean); web types updated (RouteResult), tsc+biome green. Live E2E with real OSRM + PostGIS: 0.6–0.7 s per request; with 240 seeded harassment reports across 80 segments of the short route, safety_priority switched to the longer safer alternative (3956.4 m, risk 0.023) while time/balanced kept the 3712.9 m route (risk 0.101) — preference reweighting verified. Dev-DB now carries demo evidence (Phase 7 research scenarios will re-seed/re-clean).

## Phase 5 — Anonymous Reports
- `POST /api/reports`: Pydantic validation, Redis rate limiting, duplicate/spam detection; categories per data-model.md.
- Verification state machine; `POST /api/admin/recompute` for affected segments.
- Privacy: pseudonymous, no identity fields, strip image metadata, encrypt sensitive fields.
- **Acceptance:** report → evidence → recompute pipeline working; spam/duplicate tests; privacy review checklist signed off.
- **Status: DONE (verified end-to-end).** `app/reports/` (redact, limiter, spam, store). `POST /api/reports`: Pydantic-validated category + description (≤500 chars) + optional base64 evidence image; server-side redaction of emails/phones/URLs/IPs before storage; image re-encoded (EXIF stripped) and Fernet-encrypted at rest (dev key derived when `REPORT_ENCRYPTION_KEY` unset — production must set a real key); response is content-free by design (report_id, segment_id, category, state, model_version — no description/identity/image). Rate limiting 5/h per pseudonymous client hash (Redis fixed-window, in-memory fallback); exact-duplicate detection 24 h (409); 404 unknown segment; 429; 422. `POST /api/admin/recompute`: `X-Admin-Key` gate (dev key only in development; disabled in production without `ADMIN_KEY`); recomputes engine states deterministically and persists them — reports and observations are updated via an explicit `is_report` marker on `Observation` (rowcount fallback was wrong: report and observation ids collide across tables); history trigger appends on observation changes; idempotent (second run → 0). Evidence engine surfaces reports live as `user_report` observations (reported → corroborated once ≥3 items or ≥2 source types; a report itself never conflicts — it carries no structured value). 77 tests green (ruff/mypy/format clean). Live E2E on PostGIS + Redis: report accepted with redacted description + pseudonymous client_hash; 6th report from one client → 429; duplicate → 409; evidence endpoint showed reports flowing into aggregation; recompute flipped 5 reports → CORROBORATED + stale observations reconciled, history 506 rows, rerun → 0 changed. Privacy checklist: no identity fields accepted or returned; redaction tested; metadata stripped; sensitive blob encrypted; client identifiers stored as hashes only.

## Phase 6 — ML (gated)
- Gate: exit only once a labeled dataset threshold (e.g. ≥1,000 verified observations over ≥N months) exists — never train before.
- Temporal split (train/val/test by time); XGBoost baseline vs deterministic; calibration.
- Metrics: Brier, ECE, ROC-AUC, PR-AUC, F1, feature importance; all recorded with dataset + model version in `model_versions`.
- ML in isolated module; UI/routing falls back to deterministic if model unavailable.
- **Acceptance:** metrics artifacts + versions traceable; no inventing accuracy.
- **Status: DONE (gated — no training yet, by design).** `ml/` is an isolated uv project (`[tool.setuptools] packages=["ml"]` so notebooks/ and experiments/ never collide with the package). Components: `ml/ml/gate.py` (MIN_VERIFIED_OBSERVATIONS=1000, MIN_SPAN_DAYS=90; writes `artifacts/gate-report.json`), `eval.py` (pure-stdlib Brier, ROC-AUC with tie-averaged ranks, PR-AUC, ECE, F1 — hand-computed tests), `train.py` (refuses to train while the gate is closed; exit code 3, no bypass flag), `model_registry.py` (`models/registry.json`, active_model, duplicate-registration guard), `dataset.py` (immutable timestamped CSV + manifest with dataset_version). 17 tests green (ruff clean). Live run against the real DB: gate CLOSED (0 of 251 observations verified), training refused with exit 3, dataset snapshot `ml/artifacts/dataset-20260814T062155.csv` exported (251 rows). The gate will only open once real verified evidence crosses the threshold — training then happens inside `ml/` with metrics artifacts and model version, never in the API.

## Phase 7 — Research Experiments (research-spec.md)
- Baselines: B1 shortest, B2 fastest, B3 static safety, B4 dynamic safety, B5 dynamic + uncertainty.
- Stress tests: stale, missing, noisy, conflicting evidence, day/night.
- Critical experiment lifecycle: working streetlight → simulated failure → 1 report → multiple reports → verified repair; measure old-evidence weight decay, uncertainty rise, ranking shift, confidence restore.
- **Acceptance:** every claimed metric backed by a recorded, reproducible run.
- **Status: DONE (recorded runs in `research/artifacts/`).** `research/` uv project (`api` via `[tool.uv.sources]` path dep), modules `baselines.py` / `stress.py` / `lifecycle.py`; 3 unit tests for the baseline cost; ruff clean. Baselines use the real safety_priority weights (risk weight 2.0, uncertainty 1.5) — with balanced weights the baselines degenerately agreed with B1/B2 (recorded first, then corrected). Recorded run (2026-08-14, `deterministic-baseline-v1`): seeded_area_day risk reduction B4 vs B1 = **−76.6%** at +6.6% distance / +6.6% time (B3/B4/B5 all picked the longer safer route); connaught_place and karol_bagh honestly show 0.0% (sparse evidence → all baselines agree). Stress: missing evidence → confidence 0.25 "Limited safety data"; 600-day-old single report fully expired (treated as absent); fresh report risk 0.476; 3 weak same-source reports 0.630 (confidence 0.9); conflicting evidence → confidence ×0.7 + "Conflicting recent evidence"; night/day ratio ≈ 1.42 on identical evidence; OSM lit tag without lighting evidence changes nothing (documented). Lifecycle (critical experiment): t0 freshness 1.000 → 0.549 (t30) → 0.091 (t120); uncertainty 0.300 → **0.370** on conflict; risk 0.1892 → 0.2158 (1 report) → **0.2206** (3 reports) → 0.1854 after decay — ranking shift and restore verified; confidence restore is partial while the old failure evidence is still active (honest, not a bug). All metrics in timestamped JSON+MD artifacts; the "no result without a recorded run" rule held throughout (the first baselines run with wrong weights was recorded, inspected, corrected and re-run).

## Phase 8 — Ops & Audit
- Health/monitoring, OpenTelemetry-style logging, PostGIS backup strategy, model-drift monitoring.
- Privacy/security audit, incident-response notes, dataset/model version audit trail.
- **Status: DONE.** Admin audit log: `admin_audit_log` table (append-only; stores sha256 of the admin key, never the raw key) + `audit()` on both report stores; `POST /api/admin/recompute` writes an entry per run (verified live: hashed key, recomputed=0, segments=82; failed attempts are not audited). Backup: `infra/backup.ps1` — `pg_dump` (custom format) via `docker exec` + rotation (keep newest N); verified live (339 MB dump). Model/dataset audit trail: `GET /api/models/current` returns risk_model (`deterministic-baseline-v1`), evidence_model (`evidence-baseline-v1`), `dataset_versions` from PostGIS, and the ML gate status computed from the live DB (thresholds mirror `ml/ml/gate.py`); verified live: gate closed (0 verified), dataset 20260813. Privacy review: `docs/privacy-review.md` — 8 checklist items each tied to tests or live evidence, plus honest known limitations. Dockerfile hardening: API image now runs as non-root `appuser` (uid 10001); 80 API tests green (ruff/mypy/format clean).

## Never
- invent labels, accuracy, or coverage
- scrape private location data
- train a huge model before a baseline
- claim a route is safe