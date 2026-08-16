# Map for Women

Evidence-based, uncertainty-aware safety navigation that never promises what it cannot prove.

## Overview

Map for Women is a **safety-aware navigation platform**. It combines routing,
safety evidence, freshness, confidence, uncertainty, and explainability to
provide route alternatives for women navigating urban areas — especially
after dark or in unfamiliar places.

Where conventional navigation optimizes for distance or travel time, Map for
Women also considers:

- safety-related evidence along the route (incidents, lighting, road conditions),
- how **fresh** that evidence is (it decays over time, at different rates per type),
- how **confident** the system is in its estimate (sparse or conflicting evidence lowers confidence),
- the **time of day** (night hours carry higher modeled risk),
- and **why** a route was ranked the way it was (explicit reasons, not a black-box score).

> **Map for Women estimates route risk from available evidence; it does not
> guarantee personal safety.**

The project is built as a Smart India Hackathon submission in the
women's-safety / civic-safety space, and is designed to read as a serious
engineering and research project: every safety decision is deterministic,
traceable, tested, and versioned.

## Current Status

### Implemented

- Safety-aware routing over a real road network (OSRM + PostGIS road segments)
- Three route profiles: Safety Priority, Balanced, Time Priority
- Deterministic, rule-based evidence and risk engine (transparent by design)
- Per-type evidence freshness decay and expiry
- Confidence and uncertainty reporting on every route
- Six-state evidence lifecycle (VERIFIED, REPORTED, CORROBORATED, CONFLICTING, EXPIRED, REJECTED)
- Anonymous reporting pipeline (redaction, rate limiting, deduplication, encryption)
- Map overlays: incidents, lighting, alerts, area safety, risk heatmap
- Insights page with area safety scores and area comparison
- Civic Operations page (streetlight-failure worklist, incident categories, priority areas)
- SOS panel with configurable emergency contacts and live-location sharing
- Voice input (हिंदी / English), geolocation, and live place search in the route planner
- Review Queue page: admin verify/reject of community reports (key-gated, audited)
- Dockerized 5-service stack and a one-command demo
- Automated testing: 221 Python tests, Playwright E2E suites, CI workflow

### Planned / Gated

- **ML risk model: gated.** No model has been trained; training is refused
  until ≥ 1,000 VERIFIED observations spanning ≥ 90 days exist in the database
  (see [Machine Learning](#machine-learning)).
- Larger validated dataset (real civic/NGO/helpline feeds — demo data is illustrative)
- Multi-city validation (the OSRM graph ships with a Northern-Zone/Delhi extract)
- Production-scale deployment (CORS defaults to localhost:3000, configurable via the `CORS_ORIGINS` env var; no load testing)

## Problem

- Conventional navigation focuses mainly on distance and time; it does not
  reason about safety conditions along a route.
- Safety conditions **change** — a working streetlight fails, an area becomes
  active at night — and most planners are time-of-day blind.
- Safety evidence is **incomplete** (most segments have none), **stale**
  (reports age), and **conflicting** (one report says a light works, another
  says it does not).
- Users need **explanations**, not unexplained "safety scores": why is this
  route recommended over that one, and how confident is the system?

## Solution

A three-layer system — **Evidence → Routing → Action** — in which the backend
owns every safety decision and the frontend renders what the backend decides.

### Evidence

Safety observations are stored per road segment with explicit provenance:

- observation types: incidents (harassment, suspicious activity, road hazard),
  lighting (streetlight not working, poor lighting), and others
  (blocked sidewalk, unsafe transport, other)
- source reliability (`source_type`, `source_reliability` — e.g. `demo_seed` 0.55)
- freshness (per-type exponential decay) and expiry
- confidence and verification states (six-state lifecycle)
- canonical `evidence_hash` for deduplication and traceability

### Routing

- OSRM returns candidate route geometries (3 alternatives)
- routes are map-matched onto road segments with spatial data (road type, `lit` tag)
- each segment is scored by the deterministic risk model with time-of-day context
- three profiles rank the candidates (Safety Priority / Balanced / Time Priority)
- each route returns risk probability, estimated safety, confidence,
  uncertainty, reasons, warnings, and the model version

### Action

- anonymous incident reporting (feeds back into the evidence pipeline)
- SOS panel with emergency contacts and live-location sharing
- trip sharing (share or copy a Google Maps directions link)
- Civic Operations view for streetlight-failure worklists and priority areas

## What Makes Map for Women Different

1. **Dynamic safety evidence** — routing consumes per-segment safety observations, not static ratings.
2. **Evidence freshness** — observations decay at type-specific rates and expire; stale data never masquerades as current.
3. **Uncertainty-aware routing** — sparse or conflicting evidence reduces confidence and raises uncertainty instead of creating false certainty.
4. **Explainable route ranking** — every route carries concrete reasons and warnings, plus the deterministic model version.
5. **Conflicting-evidence handling** — boolean disagreements (working vs. broken) are detected and surfaced as CONFLICTING, never silently averaged.
6. **Anonymous reporting** — reports enter the pipeline without identity and with PII redaction, and feed the evidence engine.
7. **Deterministic baseline before ML** — today's routing is fully rule-based and reproducible; ML is gated and cannot make production decisions.

These properties make the system more honest and more auditable. They are not
a claim that any route is safe.

## Key Features

### Routing

- Three route candidates per trip, each with 0–100 `estimated_safety`,
  risk probability, confidence, uncertainty, reasons, and warnings
- Time-of-day awareness: production derives IST hour; the route API accepts an
  optional `hour_ist` override, and the planner exposes a demo "simulate time"
  toggle (explicitly labeled as demo)
- Explainable route cards with per-segment evidence reasons and a
  no-safety-guarantee disclaimer
- Route comparison drawer and transport-mode selector (walking / driving / cycling)

### Live Map

- Incident, lighting, and facility overlays plus a risk-heatmap layer (default on)
- "Demo data" badge whenever seeded evidence is rendered
- 3D/2D perspective modes, layer filters, zoom controls
- Voice input for destinations (हिंदी / English, in-browser speech recognition) and
  "use my location" geolocation

### Safety & Emergency

- SOS panel with configurable emergency contacts
- Live-location sharing (share or copy a maps link)
- Share-trip links (Google Maps directions)

### Insights

- Area safety score with evidence explanation
- 7-day incidents, lighting evidence, hourly time-of-day curves
- Risk heatmap and live alerts list
- Area comparison across all monitored areas

### Civic Operations

- Streetlight-failure worklist with maps links
- Incident category breakdown and priority areas
- The same evidence municipal teams can act on (demo-seeded by default)

### Reporting

- Anonymous report form (category + description, optional image)
- PII redaction, rate limiting, duplicate detection, image metadata stripping
  and encryption on the backend

### Explainability

- Per-route reasons ("Recent incident reports on this segment", "Near an
  emergency facility", "Limited safety data for this segment", ...)
- Sparse-data and conflict warnings on routes
- Freshness and confidence surfaced per evidence type

### Privacy

- No reporter identity stored; free-text redaction; encrypted images
- Append-only evidence history; hashed admin audit trail
- Demo data explicitly labeled and excluded from the ML gate

## Route Profiles

Every request returns all three profiles, each choosing the OSRM candidate
that minimizes a weighted cost:

`C = α·distance + β·time + γ·risk + δ·uncertainty`

| Profile | α (distance) | β (time) | γ (risk) | δ (uncertainty) |
| --- | --- | --- | --- | --- |
| `safety_priority` | 0.6 | 1.0 | 2.0 | 1.5 |
| `balanced` | 1.0 | 1.0 | 1.0 | 0.8 |
| `time_priority` | 0.8 | 2.0 | 0.3 | 0.2 |

Risk is scaled to a 4,000 m walking equivalent and uncertainty to a 400 m
equivalent, so the weights are comparable. If two profiles select the same
candidate, both route types point at it — the best available candidate wins
twice, honestly.

### Safety Priority

Highest emphasis on modeled safety risk and uncertainty. Tolerates longer
distance and time to avoid risky segments.

### Balanced

Equal weight to efficiency and safety-related factors.

### Time Priority

Strongest emphasis on travel time; tolerates higher modeled risk.

No profile guarantees a safe route — all three are *recommendations* based on
available evidence.

## How It Works

```
User
  ↓  origin + destination (typed, voiced, or geolocated)
FastAPI  (POST /api/routes)
  ↓  OSRM candidate routes (3 alternatives)
Road segment mapping  (PostGIS / segment store, bbox spatial query)
  ↓
Evidence engine  (per-segment observations)
  ↓  freshness + confidence + verification states
Time/day context  (IST hour, night multiplier)
  ↓
Risk + uncertainty  (deterministic per-segment risk model)
  ↓
Route ranking  (three profiles, one candidate each)
  ↓
Frontend visualization  (map, route cards, reasons, warnings)
```

A report submitted via `POST /api/reports` is validated, redacted,
deduplicated, and rate-limited, then stored as a new observation — the next
route query sees it after evidence recomputation.

## System Architecture

```
+----------------------+          +-----------------------------------------------+
|      apps/web        |  REST    |                   apps/api                    |
|  Next.js + React +   | -------> |  FastAPI (Python 3.13, uv)                    |
|  Leaflet (pnpm)      |          |                                               |
|                      |          |  POST /api/routes ──► OSRM client ──► OSRM    |
|  Pages:              |          |       │                 (routing engine,      |
|  /live  /report      |          |       │                  walking profile)     |
|  /insights /alerts   |          |       ├──► segment matcher ──► PostGIS        |
|  /community /civic   |          |       ├──► evidence engine                    |
|                      |          |       ├──► risk model + route ranking         |
|  Renders decisions   |          |       └──► facilities (nearest emergency)     |
|  only; never invents |          |                                               |
|  safety data         |          |  GET /api/segments/{id}/evidence              |
|                      |          |  GET /api/incidents, /lighting, /alerts       |
|                      |          |  GET /api/safety/area(s), /safety/heatmap     |
|                      |          |  POST /api/reports, /api/admin/recompute      |
|                      |          |  GET /api/models/current                      |
+----------------------+          +----------------------+------------------------+
                                                          |
                                    ml/ (gated)      research/ (offline runs)
                                    Training only    recorded artifacts in
                                    after data gate  research/artifacts/
```

Responsibilities:

| Service | Responsibility |
| --- | --- |
| `apps/web` | Next.js frontend. Renders what the backend decides; never computes or invents safety data. |
| `apps/api` | FastAPI. Owns all safety decisions: routing orchestration, evidence aggregation, risk scoring, reports. |
| OSRM | Route geometry — 3 alternative candidates per request, walking/driving/cycling profiles. |
| PostGIS | Road segments (1.9M rows), facilities, safety observations, reports, append-only history tables. |
| Redis | Rate limiting and duplicate detection for reports. |
| Evidence engine | Freshness decay, verification states, conflict detection, per-type aggregation. |
| Risk engine | Deterministic per-segment risk + confidence, time-of-day weighting. |
| Route ranking | Profile-cost selection across candidates. |

Graceful degradation: if PostGIS is unreachable, the API serves a seeded
demo-evidence snapshot from memory (`EVIDENCE_SEED_JSON`), so the demo stack
still works offline.

## Safety & Risk Model

The production routing path uses the **deterministic safety baseline**
(`model_version = "deterministic-baseline-v1"`). There is no ML in the
routing path today.

Per-segment risk is a weighted combination in [0, 1]:

| Feature | Weight | Notes |
| --- | --- | --- |
| Incident evidence | 0.55 | `risk = 1 − exp(−2·incident_score)`; recency-weighted harassment + suspicious activity |
| Lighting evidence | 0.25 | `risk = 1 − exp(−1.5·lighting_score)`; streetlight failures + poor lighting + OSM `lit` tag |
| Facility proximity | 0.10 | Logistic decay vs. distance to nearest police / hospital / fire station (center 2,000 m, cutoff 3,000 m) |
| Road type | 0.10 | Footway/path/steps/cycleway/track carry elevated night risk |

Time-of-day modifiers:

- Night window (IST 20:00–04:59): combined risk × 1.35
- `lit=yes` at night: lighting risk × 0.5; `lit=no` at night: lighting risk × 1.2
- Daylight: lighting risk × 0.5; road-type risk × 0.5

Confidence per segment:

- No evidence → 0.25 ("Limited safety data for this segment")
- Base 0.6 + 0.1 per observation (up to 4)
- Conflicting evidence → × 0.7
- Cap 0.95; `uncertainty = 1 − confidence`

Reasons use a fixed vocabulary (e.g., "Recent incident reports on this
segment", "Near an emergency facility", "No emergency facility within 3 km")
and routes aggregate the top 4 with sparse-data and conflict warnings when
they exceed thresholds.

## Evidence, Freshness & Uncertainty

### Verification states

Six-state lifecycle (`app/evidence/states.py`): VERIFIED → REPORTED →
CORROBORATED → CONFLICTING → EXPIRED → REJECTED. VERIFIED and REJECTED are
immutable. State transitions never mutate rows: history tables mirror every
change (append-only).

- **REPORTED** — a single active observation
- **CORROBORATED** — ≥ 2 distinct source types, or ≥ 3 items on the same segment/type
- **CONFLICTING** — boolean disagreement on the same observation type (e.g. `working: true` vs `working: false`)
- **EXPIRED** — freshness fell below the expiry threshold
- **VERIFIED / REJECTED** — human/admin decisions, immutable

### Freshness decay

`freshness = exp(−λ · age_days)`, clamped to 0 once below the expiry
threshold (`EXPIRY_FRESHNESS = 0.05`). Decay rates are **per observation
type**:

| Observation type | λ (1/day) | Half-life |
| --- | --- | --- |
| `streetlight_not_working` | 0.02 | ~35 days |
| `poor_lighting`, `blocked_sidewalk` | 0.05 | ~14 days |
| `road_hazard`, `unsafe_transport`, `other` | 0.10 | ~7 days |
| `suspicious_activity` | 0.20 | ~3.5 days |
| `harassment` | 0.30 | ~2.3 days |

Infrastructure signals decay slowly; transient incidents decay fast.
EXPIRED observations never contribute to scores.

### Confidence, coverage & conflicts

- Per-type score = Σ (freshness × source_reliability); per-type confidence =
  `1 − exp(−2·score)` (cap 0.95; conflicting type × 0.5)
- Segment overall confidence = mean of per-type confidences; sparse segments
  show "Limited safety data" at confidence 0.25
- Route-level confidence = length-weighted aggregate; sparse fraction and
  conflict presence produce explicit route warnings

The core principle: **sparse, stale, or conflicting evidence reduces
confidence rather than creating false certainty.**

## Dynamic Data Handling

Safety conditions change over time; the system models this in several ways:

1. **Time-of-day** — implemented: IST night window multiplies risk (×1.35);
   `hour_ist` (0–23) can be supplied per request or derived from the current time.
2. **Freshness decay** — implemented: every observation ages continuously and
   expires (per-type λ above).
3. **New reports** — implemented: validated reports become observations and
   affect subsequent route queries.
4. **Streetlight lifecycle** — implemented as a *recorded research
   experiment* (`research/artifacts/lifecycle-*.md`), not as live city sensor
   data: verified working → failure reported (conflict detected, uncertainty
   rises) → multiple reports → verified repair → failure evidence decays.
   A live streetlight lifecycle would require real sensor/civic feeds, which
   are planned, not present.

> The demo's "simulate time" toggle replans with a different `hour_ist` and
> is explicitly labeled as demo simulation. The seeded streetlight data is
> illustrative demo evidence, not live telemetry.

## Data Sources & Provenance

| Source | Purpose | Status |
| --- | --- | --- |
| OpenStreetMap (via OSRM) | Route geometry, walking/driving/cycling profiles | Live — Northern-Zone extract by default; India-wide configurable |
| OpenStreetMap (via osm2pgsql loader) | Road segments with `road_type` and `lit` tags; facilities | Live — ~1.9M segments, ~3.9K facilities (loaded via `data/loaders/`) |
| Anonymous user reports | New safety observations | Live — validated, redacted, deduplicated |
| `demo_seed` evidence | Illustrative demo evidence — **not real incidents** | Seeded — 10 Delhi hotspots, `source_reliability = 0.55`, labeled in the UI, excluded from the ML gate |
| City sensors / civic feeds (streetlights, helpline stats) | Real-time safety conditions | Planned — no live integration today |

Provenance is explicit on every row: `source_type`, `source_reliability`,
`verification_state`, `observed_at`, plus a canonical `evidence_hash`
(sha256 of segment + source + type + value + time) for deduplication.
Datasets are versioned via manifests in `data/versions/` (sha256 recorded).

## Anonymous Reporting

`POST /api/reports` implements an anonymous, validated reporting pipeline:

1. **Validation** — category enum, description ≤ 500 chars, optional base64
   image ≤ 5 MB (the report page uploads JPEG/PNG up to 3.5 MB)
2. **Pseudonymization** — `client_key = sha256(request.client.host)[:16]`; the raw IP is never stored.
   `X-Forwarded-For` is ignored unless `TRUST_PROXY=1` (never trust a spoofable header by default)
3. **PII redaction** — emails, phone numbers, URLs, and IPs in descriptions → `[redacted]`
4. **Image handling** — re-encoded via Pillow (EXIF metadata stripped), then
   Fernet-encrypted at rest
5. **Duplicate detection** — 24 h window per client/segment/category → HTTP 409
6. **Rate limiting** — 5 reports/hour per client → HTTP 429
7. **Content-free response** — returns only `report_id`, `segment_id`,
   `category`, `verification_state`, `model_version`; never echoes the description
8. **Verification** — reports enter as REPORTED; admin recomputation
   (`POST /api/admin/recompute`, `X-Admin-Key`) re-derives states
   deterministically and writes an audited entry (sha256 of the admin key,
   never the raw key)

This pipeline is defense-in-depth, not a security guarantee.

## Emergency & Action Features

Frontend-only flows (no backend emergency dispatch):

- **SOS panel** — one-tap access with configurable emergency contacts
  (defined in `SOSConfirmation.tsx`): 181 Women Helpline, 112 National
  Emergency, 102 Ambulance — official Government of India numbers, editable
  as configuration
- **Live-location sharing** — share or copy a maps link of the user's current position
- **Share trip** — share or copy a Google Maps directions link for the planned route
- **Safety reporting** — the anonymous report form, attached to a segment from
  the last planned route

Emergency features are informational and configurable; the system does not
dispatch responders and makes no emergency-response guarantees.

## Privacy, Ethics & Safety

- **Anonymous reports** — no identity fields, no raw IP storage, pseudonymous
  client keys only
- **PII protection** — free-text redaction for emails/phones/URLs/IPs
- **Image metadata handling** — EXIF stripped on ingestion; images encrypted
  at rest with `REPORT_ENCRYPTION_KEY`
- **Sensitive-data protection** — admin keys hashed in audit logs; admin
  endpoints disabled in production without an `ADMIN_KEY`
- **Evidence traceability** — append-only history tables, canonical
  `evidence_hash`, versioned datasets and models
- **Uncertainty disclosure** — weak evidence lowers confidence and raises
  stated uncertainty instead of being hidden
- **Demo-data honesty** — seeded observations are labeled `demo_seed`, flagged
  in the UI, and excluded from the ML gate
- **No `safe=true`** — the API never emits a binary "safe" flag anywhere

> **Map for Women provides evidence-based navigation signals and does not
> guarantee personal safety.**

The system cannot prevent crime and does not claim to know real-time ground
truth; it estimates risk from available, decayed, possibly conflicting
evidence.

## Machine Learning

**Machine learning is currently gated and does not make production routing
decisions.** No model has been trained. This is deliberate.

The gate (`ml/ml/gate.py`, mirrored by `GET /api/models/current`):

- requires **≥ 1,000 observations in VERIFIED state**
- spanning **≥ 90 days** of observed evidence
- the label of record is the evidence engine's VERIFIED state, not a guess
- demo-seeded observations never count toward the gate

`ml/ml/train.py` refuses to run while the gate is closed (exit code 3); there
is no bypass flag.

Planned path once the gate opens:

1. immutable timestamped CSV dataset snapshots with manifests (`ml/ml/dataset.py`)
2. temporal train/validation split and baseline comparison (deterministic
   baseline is the fallback and the comparison target)
3. calibration and evaluation: Brier score, ROC-AUC, PR-AUC, ECE, F1
   (`ml/ml/eval.py`, pure-stdlib implementations)
4. versioned model registry (`models/registry.json`) with the API reporting
   the active model and gate status
5. any future model remains an *input* to the evidence/risk engine — the
   deterministic baseline stays the decision authority until replaced through
   the registry

## Research & Evaluation

Recorded, timestamped experiments live in `research/artifacts/`. Every number
below comes from a recorded run (`deterministic-baseline-v1`,
`evidence-baseline-v1`, run 2026-08-14) — it is a **configured test scenario**,
not a general real-world claim.

### Baseline comparison (B1–B5)

Shortest-path vs. dynamic-safety routing on three pairs:

| Pair | B1 (shortest) risk | B4 (dynamic safety) risk | Risk reduction | Time penalty |
| --- | --- | --- | --- | --- |
| seeded_area_day | 0.1011 | 0.0237 | 76.6% | +6.6% |
| connaught_place | 0.0132 | 0.0132 | 0.0% | 0.0% |
| karol_bagh | 0.0098 | 0.0098 | 0.0% | 0.0% |

Mean over the three pairs: 25.5% risk reduction, 2.2% time penalty. In two of
three pairs the routes coincide (no evidence difference between candidates).

### Stress tests (single-segment scenarios)

| Scenario | Result (recorded) |
| --- | --- |
| Missing evidence | risk 0.097, confidence 0.25, "Limited safety data" |
| Stale report (600 days) | fully expired → treated as absent |
| Fresh report (2 h) | risk 0.476, confidence 0.7 |
| Three weak reports, one source | risk 0.630, confidence 0.9 |
| Two corroborating sources | risk 0.620, confidence 0.8 |
| Conflicting evidence | confidence × 0.7, conflict reason surfaced |
| Night vs. day, same evidence | ratio ≈ 1.42 (night multiplier verified) |

### Streetlight lifecycle experiment

| Step | Freshness | Uncertainty | Risk | Conflict |
| --- | --- | --- | --- | --- |
| t0 verified working | 1.000 | 0.300 | 0.1892 | — |
| t30 failure reported | 0.549 | 0.370 | 0.2158 | ✓ |
| t31 multiple reports | 0.538 | 0.300 | 0.2206 | ✓ |
| t60 verified repair | 0.301 | 0.300 | 0.2196 | ✓ |
| t120 failure decayed | 0.091 | 0.300 | 0.1854 | ✓ |

The experiment demonstrates the full lifecycle the system models: report →
conflict → corroboration → verification → decay.

### Component ablation and synthetic calibration (2026-08-15)

Recorded runs (`ablation-*.json`, `calibration-*.json`):

- Leave-one-out ablation on a synthetic night corridor: incident evidence
  contributes 0.587 (61%) of risk, lighting 0.307 (32%), road 0.051 (5%),
  facility 0.017 (2%); night vs day ratio ×1.73. The mirrored component math
  is test-verified to reproduce `compute_segment_risk` exactly.
- Synthetic calibration over a 240-segment ground-truth grid: ECE 0.003,
  Brier excess over ideal 0.004, mean abs error 0.003. Ordering (Spearman
  1.0) is exact *by construction*; the run validates internal calibration
  only — real calibration needs observed outcomes from validated feeds
  (gated, none exist).

## API

Base URL: `http://localhost:8000` · Health: `http://localhost:8000/health` ·
OpenAPI/Swagger: `http://localhost:8000/docs`

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Service health + environment |
| POST | `/api/routes` | Route planning: 3 explainable profiles, risk exposure + high-risk share, off-network warnings; optional `hour_ist` override; per-IP rate limit (`ROUTE_RATE_LIMIT_PER_MINUTE`, default 30) |
| GET | `/api/geocode` | Place search (monitored areas + mapped facilities, by name) |
| GET | `/api/segments/{id}/evidence` | Aggregate evidence per segment (freshness, confidence, source counts, source-type diversity, conflicts) — never reporter identity |
| GET | `/api/incidents` | Incident markers (bbox + limit) |
| GET | `/api/lighting` | Lighting / streetlight markers |
| GET | `/api/alerts` | Recent incident alerts |
| GET | `/api/safety/area` | Area safety estimate (score, evidence, hourly curve) |
| GET | `/api/safety/areas` | All monitored areas (comparison) |
| GET | `/api/safety/heatmap` | Risk heatmap zones |
| POST | `/api/reports` | Anonymous report (validated, redacted, deduplicated, rate-limited) |
| GET | `/api/admin/reports` | Review queue — reports listed without descriptions or reporter identity (`X-Admin-Key` required) |
| POST | `/api/admin/reports/{id}/verify` | Mark a report verified (sticky across recomputes, audited) |
| POST | `/api/admin/reports/{id}/reject` | Mark a report rejected (sticky across recomputes, audited) |
| POST | `/api/admin/recompute` | Recompute verification states (`X-Admin-Key` required, audited) |
| GET | `/api/models/current` | Active model + dataset versions + ML gate status |
| POST | `/api/auth/device` | Mint a revocable device-session token for the requesting `client_id` (rate-limited) |
| POST | `/api/auth/revoke` | Revoke the current device-session token |
| GET | `/api/facilities` | Safety-relevant facilities in a bbox (police, hospital, transit, ...) |
| GET | `/api/privacy/settings` · PUT | Read / update privacy settings (voice guidance, discreet mode) |
| GET | `/api/notifications` | Recent in-app notification events for the client |

Device-session tokens (30-day TTL) are required for all personal-safety
endpoints; raw `X-Client-Id` access is disabled by default
(`ALLOW_LEGACY_CLIENT_ID=0`). See [`docs/current-status.md`](docs/current-status.md).

Full contract: [`api-spec.md`](api-spec.md).

## Technology Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, Leaflet + markercluster |
| Backend | FastAPI, Pydantic v2, SQLAlchemy, Python 3.13 (managed with `uv`) |
| Database | PostgreSQL 16 + PostGIS 3.4 |
| Routing | OSRM (custom Docker image, walking/driving/cycling profiles) |
| Caching / queue | Redis 7 |
| Infrastructure | Docker Compose (5 services), GitHub Actions CI |
| Testing | pytest + pytest-cov, mypy, ruff, Biome, Playwright E2E (Edge), `tsc` |
| ML / research | Isolated `uv` workspaces (`ml/`, `research/`) — gated training, recorded experiment artifacts |

## Project Structure

```
apps/api            FastAPI backend (uv) — safety decisions live here
apps/web            Next.js frontend (pnpm) — renders what the backend decides
infra               Docker Compose (postgis, redis, osrm, api, web) + backup.ps1
data                OSM extracts, loaders, processed evidence, versioned manifests (gitignored artifacts)
docs                Demo kit + privacy review (demo.md, sih-demo.md, pitch.html, privacy-review.md)
ml                  Gated ML workspace: gate, eval, dataset, model registry, train (refuses while gate closed)
research            Offline experiment harness: baselines, stress, lifecycle, ablation, calibration + recorded artifacts
e2e                 Playwright E2E smoke suites (verify / verify-extra / theme-check)
.github/workflows   CI: ruff, mypy, pytest on push/PR
```

Key modules under `apps/api/app/`: `api/` (HTTP endpoints), `evidence/`
(freshness, states, engine, store), `risk/` (model + routing cost), `reports/`
(redact, limiter, spam, store), `routing/` (OSRM client), `segments/`
(store + map matcher), `facilities/` (emergency facility store), `overlays/`
(incidents/lighting/alerts/heatmap), `db/` (schema + history triggers),
`seed_demo.py` (idempotent demo seeding).

## Getting Started

Prerequisites: Node.js 20.9+, `pnpm`, `uv` (Python 3.12+), Docker with
Compose (for the full stack).

```bash
git clone https://github.com/sharma9655v/Women-s-Safety.git
cd Women-s-Safety
cp .env.example .env        # development defaults are fine
pnpm install                # web dependencies
uv sync --directory apps/api
```

No API keys are required for local development. `ADMIN_KEY` and
`REPORT_ENCRYPTION_KEY` are optional in development (development-only
fallbacks exist — the encryption fallback is a random key persisted to
`.report_encryption_key`, and the dev admin key is inert unless
`ADMIN_DEV_KEY_ENABLED=1` in a `development` environment) but must be set
outside development.

## Docker Setup

```bash
docker compose -f infra/compose.yaml up --build
```

| Service | Image / build | Port | Notes |
| --- | --- | --- | --- |
| `postgis` | `postgis/postgis:16-3.4` | 5432 | schema provisioned via `apps/api/app/db/schema.sql` |
| `redis` | `redis:7-alpine` | 6379 | rate limiting, deduplication |
| `osrm` | custom build (`infra/osrm/`) | 5000 | Northern-Zone extract by default; set `OSM_PBF_URL` (e.g. `https://download.geofabrik.de/asia/india-latest.osm.pbf`) for the India-wide graph |
| `api` | custom build (non-root user) | 8000 | mounts `../data` read-only; `EVIDENCE_SEED_JSON` offline fallback |
| `web` | custom build | 3000 | `NEXT_PUBLIC_API_URL=http://localhost:8000` |

The API degrades to the in-memory demo-evidence snapshot when PostGIS is
unreachable, so the container stack stays demo-robust in constrained venues.

## Running the Application

### One-command demo

```powershell
cd infra
./demo.ps1
```

Starts all five services, seeds deterministic demo evidence, and prints URLs.
Runbook: [`docs/demo.md`](docs/demo.md). Timed judge script:
[`docs/sih-demo.md`](docs/sih-demo.md).

### Docker

```bash
docker compose -f infra/compose.yaml up --build
# web:  http://localhost:3000
# api:  http://localhost:8000  (docs at /docs)
```

### Backend development

```bash
pnpm dev:api   # uv run --directory apps/api uvicorn app.main:app --reload --port 8000
```

### Frontend development

```bash
pnpm dev:web   # pnpm --dir apps/web dev
```

### Seed demo evidence (idempotent)

```bash
uv run --directory apps/api python -m app.seed_demo
```

Writes ~340 observations across 10 Delhi hotspots as `source_type=demo_seed`;
re-running is safe (canonical `evidence_hash`, `ON CONFLICT DO NOTHING`) and
also emits `data/processed/demo-evidence.json` plus a versioned manifest.

## Testing

```bash
# API: ruff + mypy + pytest tests (scoring, evidence, reports, overlays, geocode, gates, feeds, security, auth)
uv run --directory apps/api ruff check app tests
uv run --directory apps/api mypy app
uv run --directory apps/api pytest apps/api/tests -q

# ML (18 tests) and research (21 tests) workspaces
uv run --directory ml pytest -q
uv run --directory research pytest -q

# Web: lint (Biome) + typecheck (tsc)
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck

# E2E smoke suites (web + API running; Microsoft Edge installed)
node e2e/verify.js           # 26 checks — routing, report loop, mobile, civic, console audit
node e2e/verify-extra.js     # 8 checks — SOS flow, edge cases
node e2e/theme-check.js      # light/dark/system theme behavior
```

CI (`.github/workflows/ci.yml`) runs `ruff check`, `ruff format --check`,
`mypy`, and `pytest` on every push and pull request. Latest recorded runs:
**221 Python tests green** (197 API + 9 security + 8 auth + 3 observability +
2 emergency rate limits + 2 facilities), **26/26 + 8/8 E2E checks** and all
theme checks passing.

## Limitations

- **Illustrative demo safety data** — the seeded observations are realistic
  but *not real incidents*; production safety decisions require validated
  civic/NGO/helpline feeds.
- **Uneven evidence coverage** — most road segments have no evidence;
  sparse segments are scored at confidence 0.25 and labeled "Limited safety data".
- **ML is not active** — routing runs on the deterministic baseline; the gate
  is closed by design until ≥1,000 VERIFIED observations exist over ≥90 days.
- **Geographic scope** — the OSRM graph ships with a Northern-Zone/Delhi
  extract; India-wide routing requires the full PBF download and a rebuild.
- **Verification is manual** — VERIFIED/REJECTED states come from admin
  recomputation; there is no automated cross-validation yet.
- **No field validation or load testing** — no large-scale user trial, no
  production load tests, no real-time sensor integration.
- **Operational gaps** — CORS defaults to `http://localhost:3000` (configurable via `CORS_ORIGINS`); admin audit
  has no full audit-trail UI (SQL-only for history; the Review Queue covers verify/reject);
  rate limits are per-IP-hash.
- **Demo-resilient, not fully offline** — the offline fallback is an in-memory
  evidence snapshot, not device-level caching (no PWA).

## Real data feeds (P2 groundwork)

`apps/api/app/ingest_feed.py` is a validated ingestion harness for real
civic/NGO feeds. It ships with zero real data — it is the checked path that
real feeds will take, and it enforces the evidence-integrity rules on every
row:

- required schema (segment id, observation type, JSON value, ISO-8601
  observed_at, reliability, verification state) with strict type checks;
- observation types limited to the evidence vocabulary; reliability in
  `[0, 1]`; **future-dated observations rejected**;
- reporter identity is never stored: PII/free-text columns (`description`,
  `reporter`, `email`, ...) are dropped with a warning or rejected, never
  written;
- duplicates dropped via the canonical `evidence_hash` (same idempotent
  `ON CONFLICT DO NOTHING` as the demo seeder);
- provenance is mandatory (`--source` feed name + `--licence`) and recorded in
  a versioned manifest (sha256) next to a snapshot under `data/versions/`;
- dry run by default; DB writes only with an explicit `--write` flag;
- any invalid row aborts the run — a feed is never partially ingested.

```bash
uv run --directory apps/api python -m app.ingest_feed feeds/my-feed.csv \
  --source my_feed --licence "CC BY 4.0"          # dry run
uv run --directory apps/api python -m app.ingest_feed feeds/my-feed.jsonl \
  --source my_feed --licence "CC BY 4.0" --write  # insert into PostGIS
```

Rows ingested this way count toward the ML gate only once VERIFIED (the
harness prints this warning on every run).

**First real feed — OpenStreetMap (Delhi).** `apps/api/app/osm_feed.py` fetches
live OSM data from the public Overpass API (ODbL), maps attribute tags onto the
evidence vocabulary (`lit=no` → `poor_lighting`, `sidewalk=no` → `blocked_sidewalk`,
unpaved surfaces → `road_hazard`), resolves OSM way ids to routing-graph
segment ids (`road_segments.osm_way_id`; ways absent from the graph are skipped
and counted), and feeds the harness. Recorded run (2026-08-15): **3,535
observations across 3,487 graph segments** written to PostGIS as
`source_type='osm'`, state REPORTED, `observed_at` = fetch date, reliability
0.7. Snapshot + sha256 manifest in `data/versions/` (`feed-osm-*.json`).
OSM rows are crowd-sourced and unverified: they do not count toward the ML
gate and are not VERIFIED until the admin Review Queue confirms them.

```bash
uv run --directory apps/api python -m app.osm_feed           # fetch + validate (dry run)
uv run --directory apps/api python -m app.osm_feed --write   # fetch + insert into PostGIS
```

## Roadmap

| Item | Status |
| --- | --- |
| Deterministic GIS routing + evidence pipeline | DONE |
| Rule-based safety scoring, freshness, uncertainty | DONE |
| Scoring, evidence, report, overlay, geocode, feed tests (136 API tests) | DONE |
| Reports, SOS/action flows, insights, civic ops, demo kit | DONE |
| Playwright E2E suites + CI | DONE |
| Ablation + synthetic calibration experiments (recorded runs, artifacts) | DONE — research/artifacts |
| ML training gate (≥1,000 VERIFIED observations, ≥90 days) | IN PROGRESS — gate closed, no model trained |
| Real civic/sensor data integration | IN PROGRESS — validated harness + first real feed (OSM Delhi: 3,535 REPORTED observations in PostGIS); verified/incident feeds still needed |
| Multi-city validation (India-wide OSRM graph) | PENDING / PLANNED |
| Production deployment hardening | DONE (CORS, auth layer, observability, rate limits) — load testing + monitoring still PENDING |

## Research Documentation

| Document | Contents |
| --- | --- |
| [`research-spec.md`](research-spec.md) | Research questions and hypotheses |
| [`implementation-plan.md`](implementation-plan.md) | Phase-by-phase build plan with status |
| [`design.md`](design.md) | Goals, user flow, evidence states, risk model |
| [`architecture.md`](architecture.md) | System architecture and principles |
| [`data-model.md`](data-model.md) | Table schemas, history triggers, invariants |
| [`api-spec.md`](api-spec.md) | API endpoint specifications |
| [`resources.md`](resources.md) | Data sources and resources considered |
| [`report.md`](report.md) | Full codebase analysis and SIH strategy report |
| [`docs/privacy-review.md`](docs/privacy-review.md) | Privacy checklist with evidence |
| [`docs/demo.md`](docs/demo.md) | One-command demo runbook |
| [`docs/sih-demo.md`](docs/sih-demo.md) | Timed judge demo script |
| [`docs/current-status.md`](docs/current-status.md) | Honest per-feature status, data retention, production blockers |

## Team / Contributors

Developed by the Map for Women team.

## License

License: Not yet specified.