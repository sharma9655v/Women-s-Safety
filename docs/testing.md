# Testing

All commands run from the repo root with `uv`. Current state: **259 tests
pass**, `ruff` and `mypy` clean.

## Python API

```powershell
uv run --directory apps/api pytest                 # full suite (259)
uv run --directory apps/api pytest -q -k cv        # CV endpoints + interface
uv run --directory apps/api pytest -q -k ready     # readiness checks
uv run --directory apps/api pytest -q -k metrics   # prometheus metrics
uv run --directory apps/api pytest -q -k city      # GIS validation + cities
```

Notable suites (all in `apps/api/tests/`):

| Area | Files |
| --- | --- |
| Routing (3 profiles, scoring, OSRM errors) | `test_routes.py` |
| Evidence lifecycle + conflicts | `test_evidence*.py` |
| Reports (redact, dedupe, rate-limit, encrypt) | `test_reports.py` |
| Auth (device sessions, tokens) | `test_auth.py` |
| Emergency / guardian / location sharing | `test_emergency.py`, `test_guardian*.py` |
| Rate limiting (incl. 429) | `test_rate_limit*.py` |
| CV mock/registry/endpoints | `test_cv_api.py`, `test_cv_interface.py` |
| Monitoring / readiness | `test_metrics.py`, `test_ready.py` |
| GIS multi-city validation | `test_city_validation.py` |

`/ready` tests monkeypatch `httpx.Client` (`__init__(*args, **kwargs)`)
to simulate OSRM up/down without a live router.

## Lint and types

```powershell
uv run --directory apps/api ruff check app tests
uv run --directory apps/api ruff format --check app tests
uv run --directory apps/api mypy app
```

Line length 100; mypy strict.

## Load testing — `e2e/loadtest.py`

```text
usage: python e2e/loadtest.py --base-url http://127.0.0.1:8000
       [--concurrency 50] [--duration 30] [--requests 2000]
       [--max-error-rate 0.01] [--max-p99-ms 2000]
```

- Mix: `/health`, `/api/models/current`, `/api/safety/area`,
  `/api/incidents` (curated payloads), and dynamic
  `/api/routes` calls from the Delhi pool.
- Exit codes: 0 PASS, 1 thresholds breached, 2 harness error.
- Smoke result (in-memory store): 2553 requests, 0 errors,
  ~310 req/s, p99 ~305 ms → PASS.

## E2E web checks — `e2e/verify.js`, `e2e/verify-extra.js`, `e2e/theme-check.js`

Node scripts against a running server: route cards render the required
fields, model status is honest, theme tokens match the design system.

## Android

- Unit tests: `android/app/src/test/.../DtosTest.kt` — wire-format
  contract tests (kotlinx-serialization round-trip, `ignoreUnknownKeys`).
- Run in Android Studio: `./gradlew test` (JVM unit tests),
  `./gradlew connectedAndroidTest` (instrumented, needs device).
- The app cannot be compiled on this machine (no JDK/SDK); the first
  real build must happen in Android Studio.

## Definition of done (per AGENTS.md)

API validation + errors + tests + privacy review + traceable
model/data version + uncertainty-aware UI — every new endpoint ships
with its test, its error contract and its privacy note.
