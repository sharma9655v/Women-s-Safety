# Hardening Report — Map for Women (2026-08-14 → 2026-08-16)

Scope: full production-hardening pass across the codebase — HARDEN + SECURE +
VERIFY + SIMPLIFY + DOCUMENT. No new features were added; every change either
removes a fabricated claim, closes a security gap, fixes a broken contract, or
documents a limitation. Companion doc: [`docs/current-status.md`](current-status.md).

## Verified green

- **221 Python tests** (pytest, `EXIT 0`) — 197 baseline + 9 security + 8 auth
  + 3 observability + 2 emergency rate limits + 2 facilities.
- **Frontend** — `tsc --noEmit`, Biome lint/format, `next build` all pass.
- **App import** — `app.main` imports cleanly.

## What was fixed (this pass, most recent first)

### Honesty / fabricated-data removal
- **Crowd data**: the backend fabricated `crowd` levels from incident counts
  (`overlays/store.py`) and claimed `crowd: "low"` for unknown areas
  (`api/overlays.py`). No crowd data source exists. Now: `crowd` is always
  `null`, the API schema says so, the frontend renders "Crowd level:
  unavailable — we never guess it", and the dead "Crowd" map filter was
  removed (`MapFiltersBar.tsx`, `MapCanvas.tsx`, `MapView.tsx`).
- **Invented evidence coverage**: demo score reported `coverage: 0.6`; now
  `null` (frontend shows "—" and "Coverage is not fully measured").
- **Fabricated data-source claims**: insights page claimed crowd comes from
  "transit data and community check-ins" and lighting from "city sensors" —
  both false. Reworded to community reports.
- **Misleading labels**: "Find Safe Route" → "Plan Route"; sidebar "Live Map"
  → "Map"; "Live Alerts" → "Recent Incident Reports"; "Live screen" → "Map
  screen". The E2E script was updated to match.
- **Dead contract**: `fetchSegmentsByArea` called `/api/evidence/segments`,
  which does not exist. Function removed.
- **Missing contract**: `GET /api/facilities` was called by the map but did
  not exist (404). Added a real bbox endpoint over the facilities store
  (+2 tests). The Facilities map layer now works instead of silently failing.
- **GPS honesty**: GuardianMode and LocationSharing silently swallowed
  `watchPosition` errors. Now show "Location fix lost — contacts may see an
  outdated position." and a browser-support notice.
- **Coverage honesty**: Delhi-only chips on the map and insights page.

### Security (Groups Q, C, D, E, 27)
- Dev admin key inert unless `ADMIN_DEV_KEY_ENABLED=1` AND `app_env=development`.
- Encryption fallback key now random per install, persisted to
  `.report_encryption_key` (gitignored); the old deterministic key was removed.
- `X-Forwarded-For` ignored unless `TRUST_PROXY=1` (spoofable header).
- CORS methods/headers are env-driven, no wildcards.
- **Device-session auth layer**: `POST /api/auth/device` mints a revocable
  30-day token (hashed at rest, bound to the device's `client_id`);
  `require_client_id` replaced raw `X-Client-Id` on all 10 personal-safety
  routers; legacy header access requires `ALLOW_LEGACY_CLIENT_ID=1` (off by
  default). Documented as a session layer, NOT real identity auth.
- **Rate-limit bug**: GPS location updates shared the 60/hr session-creation
  limit — a live session would 429 after ~1 minute. Split into a 600/hr
  update limiter; guardian location updates (previously unlimited) now use the
  same bound. Tests: 100 rapid updates succeed; floods 429.

### Reliability (Groups P, B, A, 24)
- **Startup hang fixed**: unbounded PostGIS connect probes (dropped packets)
  stalled registry checks for minutes; `app/db/__init__.py::make_engine()` now
  sets `connect_timeout=5` and is used at all 19 engine sites.
- **Observability**: request-ID middleware (`X-Request-Id` echoed, honored
  client ids), one structured access-log line per request with no PII.
- **Contract matrix**: every frontend `api.ts` path now maps to a live backend
  route (see fixes above); matrix script kept in
  `%TEMP%\opencode\contract_check.py`.
- **Docs**: `docs/current-status.md` (per-feature status, data retention,
  production blockers); README updated (test counts, new endpoints, auth
  notes, CORS/XFF wording, roadmap).
- Deleted dead Japanese-as-Hindi locale file.

## What was verified as already honest (no change needed)
- SOS delivery statuses (`no_channel` / `queued` / never `delivered`).
- Guardian/SOS/location sessions: client-scoped store access (foreign ids →
  404, no enumeration), uuid4 ids, TTL enforcement, bounded coordinates,
  `no fake delivery` semantics.
- Emergency sessions only after the client-side countdown; one active session.
- All "guarantee" wording in the UI is a disclaimer, not a claim.
- No "real-time"/"nationwide"/"weather" claims exist anywhere.
- Admin review queue: reports listed without descriptions or reporter
  identity; decisions sticky and audited (hashed key).
- E2E scripts consistent with current UI labels.

## Known limitations (unchanged, honest)
- SMS/Telegram provider dispatch does not exist in-repo: `notify_channel`
  records `queued`; delivery requires a deployment-side provider. UI never
  claims delivery.
- Admin key lives in browser localStorage (SIH trade-off; XSS-exposed).
- No load testing; Delhi-only OSRM graph; manual report verification.
- E2E suites (`verify.js` 26 checks, `verify-extra.js` 8, `theme-check.js`)
  require the Docker stack (Docker Desktop not running during this pass) —
  re-run them with `node e2e/verify.js` before the demo.
- No automatic data deletion (evidence history is append-only by design).

## Deployment requirements (production)
`ADMIN_KEY` · `REPORT_ENCRYPTION_KEY` · `CORS_ORIGINS` · `TRUST_PROXY=1`
(behind a stripping reverse proxy) · `ALLOW_LEGACY_CLIENT_ID=0` ·
`ADMIN_DEV_KEY_ENABLED=0` · `notify_channel` + provider if SMS/Telegram is
wanted.