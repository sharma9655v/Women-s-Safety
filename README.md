# 🛡️ Map for Women — AI-Assisted Women's Safety Navigation

> Evidence-based, uncertainty-aware safety navigation that never promises what it cannot prove.

Map for Women is a **safety-aware navigation platform** that combines routing, safety evidence,
freshness, confidence, uncertainty, and explainability to provide route alternatives for women
navigating urban areas — especially after dark or in unfamiliar places. It is built as a serious
engineering and research project: every safety decision is deterministic, traceable, tested, and
versioned.

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=flat-square&logo=next.js&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Keras](https://img.shields.io/badge/Keras-2.3-D00000?style=flat-square&logo=keras&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.3-FF6F00?style=flat-square&logo=tensorflow&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20PostGIS-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)
![OSRM](https://img.shields.io/badge/OSRM-routing-2C8EBB?style=flat-square)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?style=flat-square&logo=github-actions&logoColor=white)
![Tests](https://img.shields.io/badge/tests-221%20Python%20%2B%2034%20E2E-3FB950?style=flat-square)
![Status](https://img.shields.io/badge/status-active-2EA043?style=flat-square)

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [AI / ML Models](#ai--ml-models)
- [Model Pipeline](#model-pipeline)
- [Datasets](#datasets)
- [Training](#training)
- [Model Performance & Evaluation](#model-performance--evaluation)
- [Repository Structure](#repository-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Running the Model](#running-the-model)
- [Example Inference](#example-inference)
- [API Documentation](#api-documentation)
- [GIS / Location Intelligence](#gis--location-intelligence)
- [Safety & Responsible AI](#safety--responsible-ai)
- [Privacy & Security](#privacy--security)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [Technology Stack](#technology-stack)
- [Research & References](#research--references)
- [Testing](#testing)
- [License](#license)
- [Author / Contributors](#author--contributors)

---

## Overview

Conventional navigation optimizes for distance or travel time. **Map for Women** additionally
considers:

- **safety-related evidence** along the route — incidents, lighting, road conditions;
- **freshness** — evidence decays over time at type-specific rates and expires;
- **confidence** — sparse or conflicting evidence lowers confidence instead of creating false certainty;
- **time of day** — night hours carry higher modeled risk;
- **explainability** — *why* a route was ranked the way it was (explicit reasons, not a black-box score).

The system performs **risk estimation and route ranking** over real road networks. It does **not**
perform person classification or threat detection on imagery in its production path today; it is a
GIS + evidence-engineering system with a gated ML workspace and two trained computer-vision
checkpoints (image classification and object detection) that are **not yet integrated** into any
production decision path (see [AI / ML Models](#ai--ml-models)).

The safety decision flow is:

```text
AI Detection (gated ML — image classification + object detection checkpoints)
       ↓
Risk Analysis (deterministic evidence + risk engine, per road segment)
       ↓
Safety Decision Support (three route profiles, confidence + uncertainty)
       ↓
Alert / Dashboard / GIS Integration (maps, overlays, heatmap, SOS, reports)
```

> **Map for Women estimates route risk from available evidence; it does not guarantee personal safety.**

The system is a Smart India Hackathon submission in the women's-safety / civic-safety space.

---

## Key Features

### 🗺️ Routing

- Three route candidates per trip, each with `estimated_safety` (0–100), risk probability,
  confidence, uncertainty, reasons, and warnings
- Three explainable route profiles — **Safety Priority / Balanced / Time Priority** — with
  per-profile weighted cost selection
- Time-of-day awareness (IST night window ×1.35 risk multiplier; optional `hour_ist` override)
- Transport modes: walking / driving / cycling; route comparison drawer
- Explicit `off-network` warnings when origin/destination are > 150 m from a mapped road

### 🗄️ Evidence Engine (GIS-backed)

- Six-state observation lifecycle: `VERIFIED → REPORTED → CORROBORATED → CONFLICTING → EXPIRED → REJECTED`
- Per-type exponential freshness decay and expiry; append-only history tables
- Conflict detection for boolean disagreements (never silently averaged)
- Confidence and uncertainty reported on every segment, area, and route

### 📍 Live Map

- Incident, lighting, and facility overlays plus a risk-heatmap layer
- 3D/2D modes, layer filters, "Demo data" badge whenever seeded evidence is rendered
- Voice input (हिंदी / English) and geolocation in the route planner

### 🚨 Safety & Emergency

- SOS panel with configurable emergency contacts (181 Women Helpline, 112, 102)
- Live-location sharing with TTL and revocation; share-trip links (Google Maps)
- Guardian journey mode, journey check-ins, fake call, voice guidance, discreet mode,
  in-app notifications (backend-managed sessions)

### 📊 Insights & Civic Operations

- Area safety scores with evidence explanation; hourly time-of-day curves; area comparison
- Streetlight-failure worklist, incident category breakdown, priority areas
- Admin Review Queue (key-gated, audited) for verify / reject of reports and community posts

### 📝 Anonymous Reporting

- Validated, PII-redacted, rate-limited, deduplicated reports that feed the evidence engine
- EXIF-stripped, Fernet-encrypted images at rest; content-free API responses

### 🔐 Security

- Revocable device-session tokens (30-day TTL) for personal-safety endpoints
- Admin endpoints disabled in production without `ADMIN_KEY`; hashed audit trail
- No `safe=true` is ever emitted — the API never claims a binary "safe" flag

---

## System Architecture

```mermaid
flowchart TD
    U[User: origin + destination] --> R[POST /api/routes - FastAPI]
    R --> O[OSRM - 3 candidate routes]
    O --> M[Segment matcher - PostGIS 1.9M segments]
    M --> E[Evidence engine - freshness, states, conflicts]
    E --> T[Time-of-day context - IST night multiplier]
    T --> K[Deterministic risk + confidence model]
    K --> P[Route ranking - 3 profiles]
    P --> W[Web frontend - Next.js + Leaflet]
    P --> A[Alerts / SOS / Reports]
    K --> D[Insights + heatmap + civic ops]
    REP[POST /api/reports - anonymous] --> E
    FED[Feed ingestion - OSM Overpass / civic feeds] --> E
    ML[(ml/ - gated ML workspace)] -. no production decisions .-> K
```

| Service | Responsibility |
| --- | --- |
| `apps/web` | Next.js 16 frontend. Renders what the backend decides; never computes or invents safety data. |
| `apps/api` | FastAPI backend. Owns all safety decisions: routing orchestration, evidence aggregation, risk scoring, reports, auth. |
| OSRM | Route geometry — 3 alternative candidates per request (walking/driving/cycling). |
| PostgreSQL + PostGIS | Road segments (~1.9M rows), facilities (~3.9K), observations, reports, append-only history tables. |
| Redis | Rate limiting and duplicate detection. |
| Evidence engine | Freshness decay, verification states, conflict detection, per-type aggregation. |
| Risk engine | Deterministic per-segment risk + confidence with time-of-day weighting (`deterministic-baseline-v1`). |
| `ml/` | Gated ML workspace. Training is refused until the data gate opens; never makes production decisions. |
| `research/` | Offline experiment harness with recorded, timestamped artifacts. |

**Graceful degradation:** if PostGIS is unreachable, the API serves a seeded demo-evidence snapshot
from memory (`EVIDENCE_SEED_JSON`), so the demo stack works offline.

---

## AI / ML Models

The repository contains **two trained computer-vision checkpoints** under `models/` (added as Git
LFS-tracked artifacts) plus a **gated ML workspace** (`ml/`) whose gate is currently **closed** —
no model is registered in `models/registry.json` and **no checkpoint is wired into the routing or
risk path**. The API's active model is the deterministic rule-based baseline
(`deterministic-baseline-v1`).

The two checkpoints are documented below from the metadata embedded in the files themselves. Their
training datasets, labels, hyperparameters, and evaluation metrics are **not recorded in this
repository** `[NOT PROVIDED]`.

### `Base_model.h5` — Multi-label image classifier

| Property | Details |
| --- | --- |
| Model | `Base_model.h5` (~102 MB, Keras 2.3.0 HDF5, TensorFlow backend) |
| Architecture | VGG16 backbone (block1–3 frozen, block4–5 trainable) → BatchNorm → SE-style channel attention (1×1 convs 512→64→16→1 sigmoid, broadcast multiply) → 2× GlobalAveragePooling + `RescaleGAP` (Lambda) → Dropout(0.5) → Dense 128 (ELU) → Dropout(0.25) → Dense 20 (sigmoid) |
| Task | Multi-label image classification — 20 output units (class names not recorded in the file) `[NOT PROVIDED]` |
| Framework | Keras 2.3.0 / TensorFlow |
| Input | RGB image, 640 × 360 × 3 |
| Output | 20 sigmoid logits (multi-label) |
| Training config (embedded) | Loss: `binary_crossentropy`; metric: `accuracy`; optimizer: SGD (lr ≈ 1e-4, momentum 0.9) |
| Model File | `models/Base_model.h5` |
| Status | Trained artifact — **not integrated**; not referenced by application code; no metrics recorded `[NOT PROVIDED]` |

### `Faster_RCNN_model.hdf5` — Object detection

| Property | Details |
| --- | --- |
| Model | `Faster_RCNN_model.hdf5` (~522 MB, Keras 2.3.0 HDF5, TensorFlow backend) |
| Architecture | VGG16 feature extractor (block1–5) → Region Proposal Network (`rpn_conv1` 3×3, `rpn_out_class` 9 anchors, `rpn_out_regress` 9×4) → ROI pooling → TimeDistributed FC (25088→4096→4096) → classifier `dense_class_5` (5 logits) + `dense_regress_5` (16 = 4 classes × 4 box coords) |
| Task | Object detection — 4 foreground classes + background (class names not recorded in the file) `[NOT PROVIDED]` |
| Framework | Keras 2.3.0 / TensorFlow |
| Input | Image + region proposals (ROIs) |
| Output | Class logits + box regression deltas per ROI |
| Model File | `models/Faster_RCNN_model.hdf5` |
| Status | Trained artifact — **not integrated**; not referenced by application code; no metrics recorded `[NOT PROVIDED]` |

### ML training gate (`ml/`)

**Machine learning is gated by design.** No training may run until real labeled data exists:

- **≥ 1,000 observations in `VERIFIED` state** spanning **≥ 90 days** of observed evidence
- Demo-seeded observations (`source_type = demo_seed`) **never** count toward the gate
- `ml/ml/train.py` refuses to run while the gate is closed (exit code 3); there is no bypass flag

Recorded gate status (`ml/ml/artifacts/gate-report.json`, 2026-08-15):

```json
{
  "verified_observations": 0,
  "total_observations": 3536,
  "span_days": 4.02,
  "open": false,
  "reason": "verified observations 0 < 1000; data span 4.0 days < 90"
}
```

---

## Model Pipeline

```text
Raw Input (origin + destination)
        │
        ▼
Preprocessing (coordinate validation, OSRM candidate geometries)
        │
        ▼
Feature Extraction (map-matching onto road segments; road_type, lit tags)
        │
        ▼
Evidence Aggregation (per-type freshness × source reliability)
        │
        ▼
Deterministic Risk Model (incident / lighting / facility / road-type components)
        │
        ▼
Confidence + Uncertainty (evidence volume, conflicts, sparse-data floor)
        │
        ▼
Route Ranking (Safety Priority / Balanced / Time Priority)
        │
        ▼
Safety Decision Support (reasons, warnings, model version)
        │
        ▼
Alert / Dashboard / GIS Integration
```

The production pipeline is fully rule-based and reproducible:

1. **Input preprocessing** — coordinates are validated; OSRM returns up to 3 candidate route geometries.
2. **Feature extraction** — candidates are map-matched onto PostGIS road segments carrying
   `road_type` and `lit` tags; nearby emergency facilities are located.
3. **Evidence aggregation** — per-segment observations are decayed by age (`freshness = exp(−λ·age_days)`),
   weighted by source reliability, and combined per observation type.
4. **Model inference** — the deterministic risk model computes per-segment risk in [0, 1]
   (see below) — no ML is involved in this step today.
5. **Risk scoring** — time-of-day modifiers apply (night ×1.35; `lit`-tag adjustments).
6. **Confidence / uncertainty** — sparse segments floor at confidence 0.25; conflicts penalize ×0.7;
   `uncertainty = 1 − confidence`.
7. **Route ranking** — each profile minimizes `C = α·distance + β·time + γ·risk + δ·uncertainty`
   across the candidates.

### Per-segment risk model (deterministic baseline)

| Feature | Weight | Formula |
| --- | --- | --- |
| Incident evidence | 0.55 | `risk = 1 − exp(−2·incident_score)` (recency-weighted harassment + suspicious activity) |
| Lighting evidence | 0.25 | `risk = 1 − exp(−1.5·lighting_score)` (streetlight failures, poor lighting, OSM `lit` tag) |
| Facility proximity | 0.10 | Logistic decay vs. distance to nearest police / hospital / fire station (center 2,000 m, cutoff 3,000 m) |
| Road type | 0.10 | Footway/path/steps/cycleway/track carry elevated night risk |

Confidence per segment: no evidence → 0.25; base 0.6 + 0.1 per observation (up to 4); conflicts × 0.7;
cap 0.95.

---

## Datasets

The repository does **not ship a training dataset for the ML checkpoints** `[NOT PROVIDED]` — the
data layer contains GIS/evidence datasets used by the deterministic system, all **versioned via
sha256 manifests** in `data/versions/`:

| Dataset | Source | Contents | Status |
| --- | --- | --- | --- |
| OSM road network extract | [Geofabrik](https://download.geofabrik.de/asia/india/northern-zone-latest.osm.pbf), ODbL | `data/northern-zone-latest.osm.pbf` — Northern-Zone/Delhi extract for OSRM + osm2pgsql | Loaded — ~1.9M road segments, ~3.9K facilities |
| Demo safety evidence | `apps/api/app/seed_demo.py` | ~340 seeded observations across 10 Delhi hotspots, `source_type=demo_seed`, reliability 0.55 — **illustrative, not real incidents** | Seeded — `data/processed/demo-evidence.json` + manifests |
| OSM live feed | Overpass API, ODbL | Recorded run (2026-08-15): **3,535 observations across 3,487 graph segments**, `source_type=osm`, state REPORTED, reliability 0.7 | Loaded — `data/versions/feed-osm-*.json` |
| Facilities | OpenStreetMap (via loader) | Emergency facilities GeoJSON (police, hospital, fire, transit…) | Loaded — `data/processed/facilities-delhi-*.geojson` |
| ML dataset snapshot (export only) | `ml/ml/dataset.py` | `ml/ml/artifacts/dataset-20260814T062155.csv` — 251 rows, **0 VERIFIED**, span 2025-04-01 → 2026-08-14 | Exported — not trainable (gate closed) |

**Preprocessing / integrity rules** (enforced by `apps/api/app/ingest_feed.py` and `osm_feed.py`):

- observation types restricted to the evidence vocabulary; reliability ∈ [0, 1]; future-dated rows rejected;
- reporter identity never stored — PII/free-text columns dropped or rejected;
- duplicates removed via canonical `evidence_hash` (sha256 of segment + source + type + value + time);
- provenance mandatory (`--source` + `--licence`), recorded in versioned manifests;
- dry-run by default; any invalid row aborts the whole run.

The ML pipeline (when the gate opens) will produce immutable timestamped CSV snapshots with
manifests and a temporal train/validation split — no training set exists today.

---

## Training

**No model has been trained by the `ml/` workspace, and none can be until the data gate opens.**
This is deliberate and enforced (`ml/ml/train.py` exits with code 3 while the gate is closed).

```bash
uv run --directory ml python -m ml.train   # → "TRAINING REFUSED — gate closed"
```

| Setting | Value |
| --- | --- |
| Framework | Pure-stdlib evaluation; psycopg for DB access (ml workspace) |
| Training scripts | `ml/ml/train.py` (refuses pre-gate), `ml/ml/dataset.py` (snapshot export) |
| Gate thresholds | ≥ 1,000 VERIFIED observations over ≥ 90 days; demo data excluded |
| Batch size / epochs / optimizer / LR / loss / scheduler / augmentation | `[NOT PROVIDED]` — gated; no training run exists in this repository |
| Checkpointing | Versioned registry convention: `models/registry.json` (schema v1, currently empty) |

The two checkpoints in `models/` embed their own training configuration (see
[AI / ML Models](#ai--ml-models)) but no training logs or metrics are recorded in the repository.

---

## Model Performance & Evaluation

### Deterministic baseline — recorded research runs

Every number below comes from a **recorded, timestamped run** in `research/artifacts/`
(2026-08-14/15, `deterministic-baseline-v1`, `evidence-baseline-v1`) — a configured test scenario,
not a general real-world claim.

**Baseline comparison (B1 shortest-path vs B4 dynamic safety):**

| Pair | B1 (shortest) risk | B4 (dynamic safety) risk | Risk reduction | Time penalty |
| --- | --- | --- | --- | --- |
| seeded_area_day | 0.1011 | 0.0237 | 76.6% | +6.6% |
| connaught_place | 0.0132 | 0.0132 | 0.0% | 0.0% |
| karol_bagh | 0.0098 | 0.0098 | 0.0% | 0.0% |

Mean: 25.5% risk reduction, 2.2% time penalty (in two of three pairs the routes coincide).

**Stress tests (single-segment scenarios):**

| Scenario | Recorded result |
| --- | --- |
| Missing evidence | risk 0.097, confidence 0.25, "Limited safety data" |
| Stale report (600 days) | fully expired → treated as absent |
| Fresh report (2 h) | risk 0.476, confidence 0.7 |
| Three weak reports, one source | risk 0.630, confidence 0.9 |
| Two corroborating sources | risk 0.620, confidence 0.8 |
| Conflicting evidence | confidence ×0.7, conflict reason surfaced |
| Night vs day, same evidence | ratio ≈ 1.42 (night multiplier verified) |

**Component ablation (leave-one-out, synthetic night corridor):** incident evidence 0.587 (61% of
risk), lighting 0.307 (32%), road 0.051 (5%), facility 0.017 (2%); night/day ratio ×1.73. The
mirrored component math is test-verified to reproduce `compute_segment_risk` exactly.

**Synthetic calibration** (240-segment ground-truth grid, synthetic outcomes): ECE 0.003,
Brier excess over ideal 0.004, mean absolute error 0.003, Spearman ρ = 1.0 — **exact ordering is
*by construction***; this validates internal consistency only. Real calibration requires observed
outcomes from validated civic/NGO feeds (gated — none exist).

### ML checkpoint metrics

> Evaluation metrics for `Base_model.h5` and `Faster_RCNN_model.hdf5` (accuracy, precision,
> recall, F1, ROC-AUC, mAP) will be added only after the checkpoints are formally validated,
> registered in `models/registry.json`, and integrated. They are **not available in this
> repository today** `[NOT PROVIDED]`.

### Why recall and calibration matter for safety AI

For safety-related scoring, the cost of errors is asymmetric:

- **False negatives** (underestimating risk on a segment a user will traverse at night) are the
  most consequential failure mode — a system that misses real hazards is worse than one that is
  cautious.
- **False positives** erode trust and cause alert fatigue, but they are recoverable; the UI must
  never make them look like ground truth.
- **Calibration** matters because users act on probabilities: an overconfident "safety score"
  with no evidence behind it is a hazard of its own. This is why the system floors sparse segments
  at confidence 0.25, lowers confidence on conflicts, and never emits `safe=true`.

---

## Repository Structure

```text
Women-s-Safety/
│
├── .github/
│   └── workflows/                        # CI/CD + security scans
│       ├── ci.yml                       # ruff + format + mypy + pytest; web lint/typecheck/build
│       ├── codacy.yml                   # Codacy security analysis
│       └── fortify.yml                  # Fortify security scan
│
├── apps/
│   ├── api/                             # FastAPI backend — all safety decisions live here (uv workspace)
│   │   ├── app/
│   │   │   ├── main.py                  # FastAPI app: CORS, request-id access log, router wiring
│   │   │   ├── config.py                # Pydantic settings (env-driven)
│   │   │   ├── schemas.py               # Pydantic request/response models (incl. ML gate)
│   │   │   ├── auth.py / identity.py    # Client identity + device-session helpers
│   │   │   ├── community.py             # Community posts + moderation
│   │   │   ├── seed_demo.py             # Idempotent demo-evidence seeder (~340 obs, 10 hotspots)
│   │   │   ├── ingest_feed.py           # Validated ingestion harness for real civic/NGO feeds
│   │   │   ├── osm_feed.py              # OSM Overpass live feed (ODbL) → evidence vocabulary
│   │   │   ├── api/                     # HTTP routers (see API Documentation)
│   │   │   │   ├── routes.py            # POST /api/routes — routing orchestration
│   │   │   │   ├── reports.py           # POST /api/reports + admin verify/reject/recompute
│   │   │   │   ├── overlays.py          # /incidents /lighting /facilities /alerts /safety/*
│   │   │   │   ├── evidence.py          # GET /api/segments/{id}/evidence
│   │   │   │   ├── geocode.py           # GET /api/geocode — place search
│   │   │   │   ├── models.py            # GET /api/models/current — active model + ML gate
│   │   │   │   ├── auth.py              # POST /api/auth/device, /api/auth/revoke
│   │   │   │   ├── emergency.py         # SOS + location-sharing sessions
│   │   │   │   ├── guardian.py          # Guardian journey sessions + check-ins
│   │   │   │   ├── contacts.py          # Trusted contacts CRUD
│   │   │   │   ├── privacy.py           # Privacy dashboard + settings
│   │   │   │   ├── notifications.py     # In-app notifications
│   │   │   │   ├── community.py         # Community feed endpoints
│   │   │   │   ├── fake_call.py         # Fake-call session scheduling
│   │   │   │   ├── voice_guidance.py    # Voice guidance session start/stop/status
│   │   │   │   ├── discreet_mode.py     # Discreet-mode settings
│   │   │   │   └── preferences.py       # Routing preferences
│   │   │   ├── evidence/                # Evidence engine
│   │   │   │   ├── freshness.py         # Per-type exponential decay + expiry
│   │   │   │   ├── states.py            # Six-state lifecycle (VERIFIED…REJECTED)
│   │   │   │   ├── engine.py            # Per-type aggregation, confidence, conflicts
│   │   │   │   └── store.py             # PostGIS evidence access + demo-seed source
│   │   │   ├── risk/
│   │   │   │   ├── model.py             # Deterministic per-segment risk + confidence
│   │   │   │   └── routing.py           # Profile-cost route ranking (α/β/γ/δ weights)
│   │   │   ├── reports/                 # Anonymous reporting pipeline
│   │   │   │   ├── redact.py            # PII redaction (emails/phones/URLs/IPs)
│   │   │   │   ├── limiter.py           # Rate limiting (Redis, in-memory fallback)
│   │   │   │   ├── spam.py              # Duplicate detection (24 h window)
│   │   │   │   └── store.py             # Report persistence + image encryption (Fernet)
│   │   │   ├── routing/osrm.py          # OSRM client (3 candidates, 3 profiles)
│   │   │   ├── segments/                # Segment store + OSRM→PostGIS map matcher
│   │   │   ├── facilities/              # Emergency facility store (bbox queries)
│   │   │   ├── overlays/                # Incidents/lighting/alerts/heatmap queries
│   │   │   ├── safety/                  # SOS, guardian, sharing, check-in, discreet, voice
│   │   │   ├── notify/telegram.py       # Live Telegram delivery (optional channel)
│   │   │   ├── db/
│   │   │   │   ├── schema.sql           # Tables + append-only history triggers
│   │   │   │   └── models.py            # SQLAlchemy models
│   │   │   └── registry.py (evidence/)  # Store wiring + offline demo-evidence fallback
│   │   ├── tests/                       # 22 test modules (scoring, evidence, reports, auth, …)
│   │   ├── Dockerfile                   # Non-root API image
│   │   ├── pyproject.toml               # Dependencies + ruff/mypy/pytest config (uv)
│   │   └── .python-version
│   │
│   └── web/                             # Next.js 16 frontend — renders what the backend decides (pnpm)
│       ├── app/
│       │   ├── layout.tsx               # Root layout (PWA manifest, i18n)
│       │   ├── globals.css              # Tailwind 4 design tokens
│       │   ├── live/                    # Home: map, planner, SOS, overlays, quick actions
│       │   ├── report/                  # Anonymous report form
│       │   ├── insights/                # Area safety, trends, comparison
│       │   ├── alerts/                  # Live alerts feed
│       │   ├── community/               # Community feed
│       │   ├── civic/                   # Civic Operations (streetlight worklist, priorities)
│       │   ├── admin/                   # Review Queue (verify/reject reports + posts)
│       │   ├── contacts/                # Trusted contacts
│       │   ├── privacy/  profile/  settings/  sources/
│       │   ├── components/              # Route cards, map, emergency, safety, shell, theme, UI kit
│       │   └── manifest.ts              # PWA manifest
│       ├── lib/                         # API adapter, client-id, i18n, types, scoring helpers
│       ├── public/                      # Icons + service worker
│       ├── Dockerfile
│       ├── next.config.ts / postcss.config.mjs / tsconfig.json / biome.json
│       └── package.json
│
├── ml/                                  # Gated ML workspace (uv, Python 3.12+)
│   ├── ml/
│   │   ├── gate.py                      # Training gate (≥1,000 VERIFIED obs, ≥90 days)
│   │   ├── train.py                     # Refuses to run while gate closed (exit 3)
│   │   ├── dataset.py                   # Immutable timestamped CSV dataset snapshots
│   │   ├── eval.py                      # Pure-stdlib metrics: Brier, ROC-AUC, PR-AUC, ECE, F1
│   │   ├── model_registry.py            # models/registry.json conventions (empty today)
│   │   └── artifacts/                   # gate-report.json, dataset snapshot + manifest
│   ├── tests/                           # 18 tests (gate, registry, eval)
│   └── pyproject.toml
│
├── research/                            # Offline experiment harness (uv)
│   ├── research/
│   │   ├── baselines.py                 # B1–B5 shortest/fastest/static/dynamic/uncertainty
│   │   ├── stress.py                    # stale/missing/conflicting/day-night scenarios
│   │   ├── lifecycle.py                 # Streetlight lifecycle experiment
│   │   ├── ablation.py                  # Leave-one-out component ablation
│   │   └── calibration.py               # Synthetic calibration (Brier/ECE)
│   ├── artifacts/                       # Recorded runs: baselines-*, stress-*, lifecycle-*, …
│   ├── tests/                           # 21 tests
│   └── pyproject.toml
│
├── models/                              # Trained CV checkpoints (Git LFS-tracked)
│   ├── Base_model.h5                    # VGG16 + SE-attention, 20-class multi-label classifier
│   └── Faster_RCNN_model.hdf5           # keras-frcnn-style detector (RPN + ROI, 4 classes)
│   └── registry.json                    # [schema defined; file absent — no model registered]
│
├── data/                                # GIS data + evidence artifacts (gitignored, versioned)
│   ├── northern-zone-latest.osm.pbf     # OSM Northern-Zone/Delhi extract
│   ├── loaders/                         # fetch-osm.ps1, load-osm2pgsql.sh, load-facilities.sh
│   ├── processed/                       # demo-evidence.json, facilities-delhi-*.geojson
│   └── versions/                        # sha256 manifests (demo-evidence, feed-osm, facilities)
│
├── android/                             # Android app — Gradle scaffold (Kotlin/Compose config;
│   └── app/src/main/                    #   manifests + resources only, no Kotlin sources yet)
│
├── infra/                               # Deployment
│   ├── compose.yaml                     # 5 services: postgis, redis, osrm, api, web
│   ├── demo.ps1                         # One-command demo (build + seed + print URLs)
│   ├── backup.ps1                       # DB backup helper
│   ├── osrm/                            # Custom OSRM Docker image (Northern-Zone default)
│   └── osm2pgsql/                       # Road-segment + facility loader image
│
├── e2e/                                 # Playwright smoke suites (Edge)
│   ├── verify.js                        # 26 checks — routing, report loop, mobile, civic
│   ├── verify-extra.js                  # 8 checks — SOS flow, edge cases
│   └── theme-check.js                   # light/dark/system themes
│
├── docs/                                # Technical documentation
│   ├── current-status.md                # Honest per-feature status (Verified/Partial/Planned)
│   ├── demo.md                          # One-command demo runbook
│   ├── sih-demo.md                      # Timed judge demo script
│   ├── privacy-review.md                # Privacy checklist with evidence
│   ├── android-feature-matrix.md        # Android parity spec (planned)
│   ├── hardening-report.md / final-web-verification.md
│   └── pitch.html / pitch-assets/       # Pitch deck
│
├── api-spec.md                          # API endpoint specification
├── architecture.md                      # System architecture principles
├── data-model.md                        # Table schemas, history triggers, invariants
├── AGENTS.md                            # Agent/contributor guardrails (safety rules)
├── package.json                         # Root scripts: dev:api, dev:web, test, e2e:*
├── pnpm-workspace.yaml / pnpm-lock.yaml
├── .env.example                         # Documented environment variables
├── .gitignore / .gitattributes          # LFS filters for *.h5 / *.hdf5
└── README.md                            # This document
```

---

## Installation

### Requirements

| Requirement | Version |
| --- | --- |
| Python | 3.12+ (3.13 recommended, managed with `uv`) |
| Node.js | 20.9+ (22 used in CI) |
| Package managers | `uv`, `pnpm` (11.x) |
| Docker | with Compose (for the full stack) |
| OS | Windows / macOS / Linux (scripts include PowerShell + Bash variants) |
| GPU | Not required — no production inference runs on GPU today; ML workspace is CPU-compatible |

No API keys are required for local development.

### Setup

```bash
git clone https://github.com/sharma9655v/Women-s-Safety.git
cd Women-s-Safety
cp .env.example .env          # development defaults are fine
pnpm install                  # web dependencies
uv sync --directory apps/api  # API dependencies
uv sync --directory ml        # ML workspace (optional)
uv sync --directory research  # Research workspace (optional)
```

---

## Configuration

All configuration is environment-driven. Copy `.env.example` to `.env`:

```text
.env
├── DATABASE_URL                 # postgresql+psycopg://user:pass@host:5432/mapforwomen
├── REDIS_URL                    # redis://localhost:6379/0
├── OSRM_BASE_URL                # http://localhost:5000
├── NEXT_PUBLIC_API_URL          # http://localhost:8000 (web app)
├── SEGMENTS_GEOJSON             # Optional: load segments from GeoJSON (dev/test)
├── ADMIN_KEY                    # Admin endpoints (must be set in production)
├── CORS_ORIGINS                 # Comma-separated allowed origins (default: localhost:3000)
├── ROUTE_RATE_LIMIT_PER_MINUTE  # Per-client route limit (default 30)
├── REPORT_ENCRYPTION_KEY        # Fernet key for image encryption (production)
└── WEATHER_API_KEY              # Reserved — weather integration not implemented
```

Docker Compose additionally supports:

```text
OSM_PBF_URL        # OSM extract URL (Northern-Zone default; set to Geofabrik India for full graph)
APP_ENV            # development | production
ADMIN_DEV_KEY_ENABLED  # Dev-only admin key (inert unless development + enabled)
EVIDENCE_SEED_JSON # Offline demo-evidence fallback path
NOTIFY_CHANNEL     # none | telegram
TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID   # Live Telegram delivery (optional)
TRUST_PROXY        # 1 = trust X-Forwarded-For (default: never trust a spoofable header)
ALLOW_LEGACY_CLIENT_ID  # 0 by default — raw X-Client-Id access disabled
```

Never commit real `ADMIN_KEY` or `REPORT_ENCRYPTION_KEY` values; use `YOUR_API_KEY`-style
placeholders in any public config.

---

## Running the Application

### One-command demo

```powershell
cd infra
./demo.ps1
```

Starts all five services, seeds deterministic demo evidence, prints URLs.
Runbook: [`docs/demo.md`](docs/demo.md).

### Docker (full stack)

```bash
docker compose -f infra/compose.yaml up --build
# web:  http://localhost:3000
# api:  http://localhost:8000  (Swagger: /docs)
```

### Development (without Docker)

```bash
pnpm dev:api     # API → uvicorn app.main:app --reload --port 8000
pnpm dev:web     # Web → pnpm --dir apps/web dev
```

### Seed demo evidence (idempotent)

```bash
uv run --directory apps/api python -m app.seed_demo
```

Writes ~340 observations across 10 Delhi hotspots (`source_type=demo_seed`); safe to re-run
(canonical `evidence_hash`, `ON CONFLICT DO NOTHING`).

---

## Running the Model

### ML gate status

```bash
uv run --directory ml python -m ml.gate
```

### Dataset snapshot (immutable export)

```bash
uv run --directory ml python -m ml.dataset
```

### Training (refused while gate closed)

```bash
uv run --directory ml python -m ml.train   # exit code 3 while the gate is closed
```

### Research experiments (recorded runs)

```bash
uv run --directory research python -m research.baselines    # B1–B5 over real OD pairs (needs stack)
uv run --directory research python -m research.stress       # stale/missing/conflicting scenarios
uv run --directory research python -m research.lifecycle    # streetlight lifecycle experiment
uv run --directory research python -m research.ablation     # leave-one-out component ablation
uv run --directory research python -m research.calibration  # synthetic calibration
```

### Real-data feed ingestion

```bash
uv run --directory apps/api python -m app.ingest_feed feeds/my-feed.csv \
  --source my_feed --licence "CC BY 4.0"                     # dry run
uv run --directory apps/api python -m app.ingest_feed feeds/my-feed.jsonl \
  --source my_feed --licence "CC BY 4.0" --write             # insert into PostGIS

uv run --directory apps/api python -m app.osm_feed           # OSM Overpass fetch + validate
uv run --directory apps/api python -m app.osm_feed --write   # fetch + insert into PostGIS
```

---

## Example Inference

### Route risk inference (`POST /api/routes`)

```text
Input (origin + destination)
   ↓
Preprocessing (validation, OSRM candidates)
   ↓
Segment matching (PostGIS)
   ↓
Evidence aggregation + risk model (deterministic-baseline-v1)
   ↓
Prediction (per-profile: risk probability, estimated_safety, confidence, uncertainty)
   ↓
Confidence / risk scores with reasons + warnings
```

Request (as specified in `api-spec.md`):

```json
{
  "origin": {"lat": 28.61, "lon": 77.23},
  "destination": {"lat": 28.63, "lon": 77.21},
  "mode": "walking",
  "safety_preference": "safety"
}
```

Response fields (per route type): `distance`, `duration`, `risk_probability`,
`estimated_safety` (0–100), `confidence`, `uncertainty`, `warnings`, `reasons`,
`model_version`, plus `high_risk_fraction` (0–1) and `risk_exposure_m`.

> Values are intentionally **not** hardcoded here — responses depend on live evidence in the
> database. Recorded example outcomes for a configured test scenario are in the
> [Model Performance](#model-performance--evaluation) section.

### Model endpoints

- `GET /api/models/current` returns the active model (`deterministic-baseline-v1`,
  `evidence-baseline-v1`), dataset versions, and the ML gate status (`open: false` today).
- The CV checkpoints in `models/` have **no inference endpoint** — they are not integrated.

---

## API Documentation

Base URL: `http://localhost:8000` · Health: `/health` · OpenAPI/Swagger: `/docs`
Full contract: [`api-spec.md`](api-spec.md)

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Service health + environment |
| POST | `/api/routes` | Route planning — 3 explainable profiles, risk exposure, warnings; optional `hour_ist`; per-IP rate limit |
| GET | `/api/geocode` | Place search (monitored areas + facilities, by name) |
| GET | `/api/segments/{id}/evidence` | Aggregated per-segment evidence (freshness, confidence, conflicts) — never reporter identity |
| GET | `/api/incidents` · `/api/lighting` · `/api/alerts` | Map overlay markers (bbox + limit) |
| GET | `/api/safety/area` · `/api/safety/areas` · `/api/safety/heatmap` | Area safety estimate, comparison, risk heatmap |
| GET | `/api/facilities` | Safety-relevant facilities in a bbox |
| POST | `/api/reports` | Anonymous report (validated, redacted, deduplicated, rate-limited) |
| GET | `/api/admin/reports` | Review queue — descriptions/identity never returned (`X-Admin-Key`) |
| POST | `/api/admin/reports/{id}/verify` · `/reject` | Sticky, audited verification decisions |
| POST | `/api/admin/recompute` | Deterministic recomputation of verification states |
| GET | `/api/models/current` | Active model + dataset versions + ML gate status |
| POST | `/api/auth/device` · `/api/auth/revoke` | Mint / revoke device-session tokens |
| GET/POST/PUT/DELETE | `/api/contacts` | Trusted contacts |
| GET/POST | `/api/community`, `/api/admin/community/{id}/verify|reject` | Community feed + moderation |
| POST | `/api/emergency/sessions` family | SOS sessions, location sharing (TTL, revocable) |
| POST | `/api/guardian/sessions` family | Guardian journeys, check-ins, deviation detection |
| POST | `/api/journey/checkins` | Timed/destination check-in sessions |
| GET/POST | `/api/fake-call`, `/api/voice/*`, `/api/discreet-mode`, `/api/preferences` | Emergency-adjacent tooling |
| GET | `/api/privacy/dashboard` · `/api/privacy/settings` | Privacy dashboard + settings |
| GET | `/api/notifications` | In-app notification events |

**Error semantics:** duplicate reports → `409`; rate limits → `429`; bad coordinates →
`4xx`; unknown admin targets → `404`; admin endpoints without a valid `X-Admin-Key` → `403`;
admin endpoints in production without `ADMIN_KEY` → `503`.

**Authentication:** personal-safety endpoints require a device-session bearer token
(30-day TTL, revocable). Raw `X-Client-Id` access is disabled by default
(`ALLOW_LEGACY_CLIENT_ID=0`).

---

## GIS / Location Intelligence

- **Road network:** OSRM (custom Docker image, walking/driving/cycling profiles) over a
  Northern-Zone/Delhi OSM extract; ~1.9M road segments loaded into PostGIS via
  `data/loaders/` (osm2pgsql), carrying `road_type` and `lit` tags.
- **Map matching:** OSRM route geometries are map-matched onto PostGIS segments; unmatched
  requests produce explicit off-network warnings.
- **Overlays:** incidents, lighting, facilities, alerts, and a risk-heatmap layer served by
  `GET /api/incidents|lighting|alerts|safety/heatmap` and rendered by Leaflet on the web.
- **Facilities:** ~3.9K emergency facilities (police, hospital, fire, transit) with
  logistic-decay proximity risk in the risk model.
- **Spatial queries:** bbox-based segment/evidence/facility queries; area-level safety scores
  aggregated from segment evidence; hourly time-of-day curves per area.
- **Versioning:** every ingested dataset is recorded in `data/versions/` with a sha256 manifest,
  so any map/risk computation is reproducible from a pinned extract.

**Integration with the ML system:** the deterministic risk engine consumes GIS-derived features
(road type, `lit` tags, facility distance). A future gated model would consume the same evidence
features (see `ml/ml/dataset.py` export schema) and would remain an *input* to the evidence/risk
engine — never a replacement without registry sign-off.

---

## Safety & Responsible AI

This system is **decision-support technology, not an autonomous authority**.

- **The model should not be used as the sole basis for accusing, identifying, or taking
  enforcement action against an individual.** No component identifies persons, vehicles, or
  offenders; the API never emits `safe=true`.
- **False positives** (overstated risk) are surfaced with their evidence and confidence so users
  can weigh them; the UI shows exactly why a route was ranked.
- **False negatives** (understated risk) are mitigated by conservative defaults: sparse segments
  are floored at confidence 0.25, stale evidence expires and never masquerades as current, and
  conflicts reduce confidence instead of being averaged away.
- **Dataset bias:** today's evidence is demo-seeded (labeled in the UI and excluded from the ML
  gate) or OSM-derived (unverified). Real risk distributions require validated civic/NGO/helpline
  feeds; until then no real-world accuracy claim is made.
- **Domain shift:** the OSRM graph is a Northern-Zone/Delhi extract; risk estimates are not
  transferable to other cities without rebuilding the graph and re-validating.
- **Model uncertainty** is explicit: confidence and uncertainty are returned per route and per
  segment, and weak evidence never pretends to be strong.
- **Human oversight:** `VERIFIED`/`REJECTED` states are human/admin decisions via the Review
  Queue, audited with hashed admin keys.
- **Responsible deployment:** alerts should be **independently verified before escalation**;
  emergency features are informational and configurable — the system dispatches no responders
  and makes no emergency-response guarantees.

---

## Privacy & Security

| Concern | Implementation |
| --- | --- |
| Reporter identity | Never stored. Reports are pseudonymized (`client_key = sha256(IP)[:16]`); raw IPs never persisted; `X-Forwarded-For` ignored unless `TRUST_PROXY=1`. |
| PII | Free-text redaction of emails, phones, URLs, IPs in descriptions. |
| Images | Re-encoded via Pillow (EXIF stripped), Fernet-encrypted at rest (`REPORT_ENCRYPTION_KEY`). |
| Location data | Location sharing is explicit opt-in with TTL and revocation; GPS failures surfaced honestly. |
| Data retention | Evidence rows are append-only; history tables mirror every state change; demo data clearly labeled. |
| Authentication | Revocable device-session tokens (30-day TTL, hashed storage); personal endpoints require bearer tokens. |
| API security | Per-IP rate limiting (reports, routes, auth, sessions); request-id access log without query strings or bodies (no PII logged). |
| Secrets management | `ADMIN_KEY`/`REPORT_ENCRYPTION_KEY` required outside development; admin keys stored hashed in audit logs; dev fallbacks inert outside `development` + opt-in flags. |
| Encryption | Fernet at rest for report images; Telegram credentials only used when `NOTIFY_CHANNEL=telegram`. |

This is defense-in-depth, not a security guarantee.

---

## Limitations

- **Illustrative demo safety data** — seeded observations are realistic but *not real
  incidents*; production safety decisions require validated civic/NGO/helpline feeds.
- **ML is not active** — routing runs on the deterministic baseline; the gate is closed by
  design until ≥ 1,000 VERIFIED observations exist over ≥ 90 days. The CV checkpoints in
  `models/` are **not integrated** and have no recorded metrics or training provenance in this
  repository.
- **Uneven evidence coverage** — most road segments have no evidence; sparse segments score at
  confidence 0.25 with "Limited safety data".
- **Geographic scope** — OSRM graph ships with a Northern-Zone/Delhi extract; India-wide routing
  requires the full PBF download and a rebuild.
- **Verification is manual** — VERIFIED/REJECTED states come from admin review; no automated
  cross-validation yet.
- **No field validation or load testing** — no large-scale user trial, no production load tests,
  no real-time sensor integration (streetlight lifecycle is a recorded research experiment only).
- **Operational gaps** — CORS defaults to `http://localhost:3000`; rate limits are per-IP-hash;
  audit history has no dedicated UI; offline fallback is an in-memory snapshot, not device-level
  caching (no PWA).
- **Android app** — the `android/` folder contains Gradle build configuration and resources only;
  no Kotlin sources are present yet (see `docs/android-feature-matrix.md` for the planned parity).

---

## Roadmap

| Item | Status |
| --- | --- |
| Deterministic GIS routing + evidence pipeline | ✅ DONE |
| Rule-based safety scoring, freshness, uncertainty | ✅ DONE |
| Reports, SOS/action flows, insights, civic ops, demo kit | ✅ DONE |
| Playwright E2E suites + CI | ✅ DONE |
| Ablation + synthetic calibration experiments (recorded runs) | ✅ DONE |
| Auth hardening, observability, rate limits, admin review | ✅ DONE |
| ML training gate (≥ 1,000 VERIFIED observations, ≥ 90 days) | 🔄 IN PROGRESS — gate closed, no model trained |
| Real civic/sensor data integration | 🔄 IN PROGRESS — validated harness + first real feed (OSM Delhi: 3,535 REPORTED observations) |
| CV model integration (classification + detection checkpoints) | ⬜ PENDING — checkpoints present, not registered or wired |
| Multi-city validation (India-wide OSRM graph) | ⬜ PLANNED |
| Production load testing + monitoring | ⬜ PENDING |
| Android app implementation (Kotlin sources) | ⬜ PENDING — scaffold + parity matrix defined |

---

## Technology Stack

| Technology | Purpose |
| --- | --- |
| Python 3.13 | Core backend + ML/research workspaces (`uv`-managed) |
| FastAPI + Pydantic v2 | REST API, validation, OpenAPI docs |
| Next.js 16 / React 19 / TypeScript | Web frontend |
| Tailwind CSS 4 / Biome / `tsc` | Styling, linting, typechecking |
| Leaflet + markercluster | Map rendering |
| PostgreSQL 16 + PostGIS 3.4 | Road segments, evidence, reports, spatial queries |
| OSRM | Route geometry (3 candidates, 3 transport profiles) |
| Redis 7 | Rate limiting, deduplication |
| Keras 2.3 / TensorFlow | Trained CV checkpoints (`models/`) — not yet integrated |
| Docker Compose | 5-service deployment |
| pytest / mypy / ruff / Playwright | Testing, typing, linting, E2E |
| GitHub Actions | CI (`ci.yml`) + security scans (Codacy, Fortify) |

---

## Research & References

The repository does not cite external research papers. It builds on the following
data/tooling (all referenced by the project's own documentation):

| Reference | Role |
| --- | --- |
| [OSRM Project](https://project-osrm.org/) | Open-source routing engine (walking/driving/cycling profiles) |
| [OpenStreetMap](https://www.openstreetmap.org/) — ODbL | Road network, `lit` tags, facilities; live Overpass feed |
| [Geofabrik](https://download.geofabrik.de/asia/india/) — ODbL | Regional OSM extracts (Northern-Zone default, India-wide configurable) |
| [PostGIS](https://postgis.net/) | Spatial storage and query layer |
| [keras-frcnn](https://github.com/yhenon/keras-frcnn) architecture | Structural reference for the `Faster_RCNN_model.hdf5` checkpoint (RPN + ROI layout matches) |
| Government of India helplines | 181 Women Helpline, 112 National Emergency, 102 Ambulance (configurable SOS contacts) |

Research experiments and their recorded results: `research/README.md` and `research/artifacts/`
(baselines, stress, lifecycle, ablation, calibration — every number traceable to a timestamped run).

---

## Testing

```bash
# API: lint + types + tests
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
node e2e/verify.js          # 26 checks — routing, report loop, mobile, civic, console audit
node e2e/verify-extra.js    # 8 checks — SOS flow, edge cases
node e2e/theme-check.js     # light/dark/system themes
```

CI (`.github/workflows/ci.yml`) runs `ruff check`, `ruff format --check`, `mypy`, and `pytest`
on the API workspace and lint + typecheck + build on the web workspace for every push/PR.
Latest recorded runs: **221 Python tests green** (197 API + 9 security + 8 auth + 3 observability
+ 2 emergency rate limits + 2 facilities) and **26/26 + 8/8 E2E checks** passing.

---

## License

No open-source license has currently been specified. All rights reserved until a license is
chosen by the maintainers.

---

## Author / Contributors

| | |
| --- | --- |
| Repository | [github.com/sharma9655v/Women-s-Safety](https://github.com/sharma9655v/Women-s-Safety) |
| Maintainer (from git metadata) | Vashudev Sharma — [@sharma9655v](https://github.com/sharma9655v) |
| Team | Map for Women team (additional contributions recorded in git history) |

---

*Map for Women provides evidence-based navigation signals and does not guarantee personal
safety. It estimates risk from available, decayed, possibly conflicting evidence — and says so.*
