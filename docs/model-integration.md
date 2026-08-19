# Model integration

How models are registered, versioned, gated and (eventually) served —
without ever pretending unvalidated models are in production.

## Registry — `models/registry.json`

`schema_version: 2`. Current entries (both `VALIDATION_REQUIRED`,
`metrics: {}`, `integration: not_integrated`):

| name | version | kind | framework | checkpoint |
| --- | --- | --- | --- | --- |
| base_model | v1 | cv_classifier | keras | models/Base_model.h5 |
| faster_rcnn | v1 | cv_object_detector | keras-frcnn | models/Faster_rcnn.h5 |

Status vocabulary (enforced):

- `AVAILABLE` — checkpoint present, not yet validated.
- `EXPERIMENTAL` — in research use, labelled.
- `VALIDATION_REQUIRED` — present, must be validated before any use.
- `PRODUCTION` — validated on real data with published metrics;
  **never** assigned to an unvalidated checkpoint.

A checkpoint may only become `PRODUCTION` after the ML gate opens
(see below) and validation metrics are recorded in the registry entry.

## ML gate — `ml/ml/gate.py`

- Open only when ≥ 1,000 **VERIFIED** observations span ≥ 90 days.
- `demo_seed` and `fixture` observations never count.
- Current report: verified=0, total=3536, span≈4.0 days → **closed**.
- The API exposes the live gate state at `GET /api/models/current`
  (`ml_gate` object) — the UI renders it, it never fabricates a model.

## CV backend — `apps/api/app/cv/`

- `interface.py` — `CVBackend` protocol: `load()`, `predict()`,
  `is_loaded()`, `is_real_inference`, `health()`.
- `mock_impl.py` — the default development backend. It returns
  deterministic placeholder outputs and MUST report
  `is_real_inference=False`; the API surfaces this in `/api/cv/health`.
- `preprocess.py` / `postprocess.py` — image normalization
  (640×360×3 float) and output decoding.
- `registry.py` — reads `models/registry.json` from the repo root
  (`parents[4]` of the module file).
- Selection: `CV_BACKEND=mock|disabled|real`. `real` imports
  `CV_REAL_BACKEND_MODULE` (e.g. `app.cv.keras_impl`) which must exist
  and load the validated checkpoint; empty module → backend disabled.

Endpoints: `GET /api/cv/models`, `GET /api/cv/health`,
`POST /api/cv/predict` (400 invalid image / 404 unknown model /
503 disabled-or-unloaded / 504 timeout, `CV_INFERENCE_TIMEOUT_S`).

## Active models — `apps/api/app/api/models.py`

- `RISK_MODEL = "deterministic-baseline-v1"` (routing risk scorer)
- `EVIDENCE_MODEL = "evidence-baseline-v1"` (evidence aggregation)
- `set_active_model(...)` records the active model + gate state into
  `/metrics`; `/api/models/current` returns the same data plus
  `cv_models` from the registry.

## Rules of the road

1. Mock inference never calls itself real; real backends never run
   before validation.
2. Every route/evidence response carries its `model_version`.
3. Registry edits are human-reviewed, schema-versioned JSON (no code
   changes required to register a new checkpoint).
4. When a validated checkpoint arrives: register it → validate →
   record metrics → `PRODUCTION` → switch `CV_BACKEND=real`.
