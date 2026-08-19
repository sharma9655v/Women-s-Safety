# API reference (current state)

Base URL: `http://localhost:8000` (dev). OpenAPI docs at `/docs`.

All private endpoints resolve the pseudonymous client either from a
`Authorization: Bearer <device-session-token>` header (Android app) or the
`X-Client-Id` header when `ALLOW_LEGACY_CLIENT_ID=1` (dev/test only).
Production keeps `ALLOW_LEGACY_CLIENT_ID=0`: the header is self-asserted
and not trusted on its own.

## System

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness (always 200 when the process is up) |
| GET | `/ready` | Readiness: 200 when DB (if configured), OSRM and CV backend are all healthy; 503 otherwise |
| GET | `/metrics` | Prometheus text format (in-process counters; not in OpenAPI) |

`/ready` checks, in order:
1. Database — only when `DATABASE_URL` is set (in-memory mode skips it).
2. OSRM — probes `route/v1/walking/...` with a 2 s timeout.
3. CV — `get_cv_service().is_loaded()`; the mock is always loaded,
   `disabled` backend reports 503.

## Routing

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/routes` | 3 ranked route profiles (safety / balanced / time). Body: `origin`, `destination` (`{lat,lon}`), `mode`, `safety_preference`, `hour_ist`. Rate limit `ROUTE_RATE_LIMIT_PER_MINUTE` (default 30) → 429. Errors: OSRM down → 503; off-network endpoints → 4xx with explicit warnings. |

## Evidence & reports

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/segments/{id}/evidence` | Aggregated evidence: freshness, confidence, source counts, diversity, conflicts. Never returns reporter identity. |
| POST | `/api/reports` | Anonymous report. `segment_id`, `category`, optional `description` (redacted, ≤500 chars), optional `evidence_image` (base64; EXIF-stripped, re-encoded, Fernet-encrypted). 5/hour/client → 429. Duplicates within 24 h → 409. |

## Emergency / guardian / sharing

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/emergency/sessions` | Create SOS session (one active per client → 409). |
| GET | `/api/emergency/sessions/active` | Active session or `null`. |
| POST | `/api/emergency/sessions/{id}/location` | Update location. |
| POST | `/api/emergency/sessions/{id}/end` | End session. |
| POST | `/api/guardian/sessions` | Start guardian journey (one active → 409). |
| GET | `/api/guardian/sessions/active` | Active journey or `null`. |
| POST | `/api/guardian/sessions/{id}/location` | Update location. |
| POST | `/api/guardian/sessions/{id}/checkin` | Manual check-in. |
| POST | `/api/guardian/sessions/{id}/end` | End journey. |
| POST | `/api/location-sharing/...` | Explicit opt-in sharing with TTL (see `app/api/emergency.py`). |
| GET | `/api/location-sharing/active` | Active sharing session or `null`. |

Notifications carry an honest status: `no_channel` unless a real channel
(`NOTIFY_CHANNEL=telegram` + credentials) is configured; `delivered` is
only reported after a provider confirms delivery.

## Contacts / preferences / privacy

| Method | Path | Description |
| --- | --- | --- |
| GET/POST | `/api/contacts` | List / create trusted contacts. |
| PUT/DELETE | `/api/contacts/{id}` | Update / delete (204). |
| GET/PUT | `/api/preferences` | Per-client preferences. |
| GET | `/api/privacy` | What this client has stored (self-service transparency). |

## Models, CV, geocode, community

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/models/current` | `risk_model`, `evidence_model`, `dataset_versions`, `ml_gate` (`open`, verified counts/span, thresholds), `cv_models` (registry metadata). |
| GET | `/api/cv/models` | Registry entries from `models/registry.json`. |
| GET | `/api/cv/health` | `backend`, `loaded`, `is_real_inference`, model count. |
| POST | `/api/cv/predict` | Image classification via the active CV backend (mock by default; 400 invalid image, 404 unknown model, 503 backend disabled/unloaded, 504 timeout). |
| GET | `/api/geocode?q=...&limit=6` | Place search over monitored areas + facilities; no external service. |
| GET/POST | `/api/community/posts` | Community feed (PENDING + VERIFIED only on the public list). |
| POST | `/api/admin/...` | Admin queue, verify/reject, recompute (`X-Admin-Key`; 403 without it; 503 in production without `ADMIN_KEY`). |

## Auth

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/auth/device` | Create a device session: body `{"client_id": "..."}` → `{token, expires_at}`. Token is revocable, 30-day TTL, stored hashed. |

## Errors

- All errors are JSON `{"detail": ...}` with correct status codes.
- A catch-all handler returns a sanitized 500 (no stack traces, no
  internals) and records the failure in `/metrics`.
- Uncaught routing/OSRM failures never fabricate a route.

See `apps/api/app/api/*.py` for the authoritative schemas.
