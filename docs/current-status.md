# Current Status — Map for Women (hardening pass, 2026-08-16)

Honest status of every part of the system. Each item is either **Verified**
(test/CI green), **Partial** (works with known caveats), **Not Implemented**,
or **Dependency** (requires an external party). Nothing here is aspirational:
if it is not in this file as Verified, assume it does not work yet.

## 1. Routing

| Item | Status | Evidence |
| --- | --- | --- |
| Three route profiles (safety / balanced / time) | Verified | `tests/test_routes.py`, E2E verify.js |
| Deterministic risk + confidence + uncertainty per segment | Verified | `tests/` scoring suite, `research/artifacts/` |
| Time-of-day weighting (`hour_ist`) | Verified | night multiplier ratio ≈ 1.42 recorded |
| OSRM integration | Verified (local graph) | Northern-Zone/Delhi extract only |
| Off-network / unmatchable requests | Verified | graceful 4xx + warnings |
| ML in the routing path | Not Implemented | gate closed; no model exists |

## 2. Evidence engine

| Item | Status | Evidence |
| --- | --- | --- |
| Six-state lifecycle + append-only history | Verified | `tests/`, schema triggers |
| Per-type freshness decay + expiry | Verified | decay suite |
| Conflict detection (boolean disagreements) | Verified | CONFLICTING surfaced, never averaged |
| Evidence endpoint `/api/segments/{id}/evidence` | Verified | frontend adapter renders it |
| Real crowd data | Not Implemented | **no crowd data source exists** — API returns `crowd: null` and the UI says "not available"; the map's crowd filter was removed |
| Weather integration | Not Implemented | no claims made anywhere |
| Streetlight live sensors | Not Implemented | recorded research experiment only, labeled as such |

## 3. Reports & admin

| Item | Status | Evidence |
| --- | --- | --- |
| Anonymous report pipeline (redact, dedupe, rate limit, encrypt) | Verified | `tests/test_reports.py` |
| Image re-encode + EXIF strip + Fernet at rest | Verified | redact tests |
| Encryption key fallback | Verified | random per-install key persisted to `.report_encryption_key` (gitignored); deterministic fallback removed |
| Rate limiting (reports, routes, auth, sessions, GPS updates) | Verified | `tests/`, incl. 429 tests |
| XFF trust gate (`TRUST_PROXY`) | Verified | spoofed `X-Forwarded-For` ignored by default |
| Dev admin key | Partial | inert unless `ADMIN_DEV_KEY_ENABLED=1` AND `app_env=development` |
| Admin review queue + verify/reject + recompute | Verified | `tests/`, `/admin` page, audited (hashed key) |
| Community moderation (verify/reject posts) | Verified | backend endpoints + dedicated UI on `/admin` ("Community posts" card: PENDING posts with Verify/Reject, X-Admin-Key header, live-tested PENDING → VERIFIED, wrong key 403); public feed shows PENDING + VERIFIED only |
| Automated verification of reports | Not Implemented | VERIFIED is a human decision; no auto cross-validation |

## 4. Emergency / SOS / location

| Item | Status | Evidence |
| --- | --- | --- |
| SOS sessions (countdown-gated, one active, client-scoped 404s) | Verified | `tests/test_emergency.py` |
| Honest notification status (`no_channel` / `queued` / never `delivered`) | Verified | UI explicitly says "NOT notified automatically" without a provider |
| Location sharing (explicit opt-in, TTL, revocable) | Verified | `tests/` |
| GPS failure honesty (watchPosition errors surfaced) | Verified | GuardianMode + LocationSharing show a warning instead of pretending |
| Real SMS/Telegram provider dispatch | Partial | **live Telegram delivery implemented** (`app/notify/telegram.py`): with `NOTIFY_CHANNEL=telegram` + `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` the API actually sends and records `sent`/`failed`; SMS remains `queued` (no provider); without credentials the honest status is `no_channel` |
| Offline / network-loss banner | Verified | live page banner on `offline` events |

## 5. Auth & security (hardening pass)

| Item | Status | Evidence |
| --- | --- | --- |
| Revocable device-session tokens (30-day TTL, hashed storage) | Verified | `tests/test_auth.py` (8) |
| Raw `X-Client-Id` access disabled by default | Verified | `ALLOW_LEGACY_CLIENT_ID=0`; 401 without a token |
| All personal-safety routers moved to `require_client_id` | Verified | 10 routers swapped |
| CORS: env-driven origins/methods/headers, no wildcards | Verified | `tests/test_security.py` |
| Request-ID middleware + access log (no PII in logs) | Verified | `tests/test_observability.py` (3) |
| Session IDs unguessable (uuid4), locations bounded | Verified | code + tests |
| GPS location-update rate limits (600/hr, not 60/hr) | Verified | `tests/test_emergency.py` — 100 rapid updates succeed, floods 429 |
| Admin key in browser localStorage | Partial | pragmatic SIH choice; XSS-exposed if the web origin is compromised |
| Identity/auth beyond pseudonymous sessions | Not Implemented | deliberately out of scope; this is NOT real user authentication |

## 6. Frontend

| Item | Status | Evidence |
| --- | --- | --- |
| PWA (manifest + service worker) | Verified | `app/manifest.ts` + `/icon.svg` + `/sw.js`; SW caches static assets + app shell only, **never** `/api/` responses (stale safety data never served); registered only on https/localhost; live 200 |
| "Riskier tonight" time-of-day chip | Verified | replans selected trip at 22:00 IST via real `/api/routes`; verified delta CP→Saket 1.42% → 2.62%; chip renders only when the model actually says riskier, with "model estimate, not a guarantee" footnote |
| A11y pass | Verified | Modal + Drawer: focus trap, initial focus, restore-on-close, Escape; SOS countdown `aria-live="polite"`; icon buttons all labeled |
| Hindi / English UI toggle | Verified | `lib/i18n.tsx` (I18nProvider, `mf:lang` localStorage); sidebar nav + bottom links, top header (search placeholder, region, theme/lang labels), mobile nav tabs, emergency card wired via `t()`; typecheck/build green; pages 200 |
| Landing page at `/` (story page) | Verified | hero, pipeline, verified numbers (1.88M segments / 3.9K facilities / 228 tests / 34-34 smoke / 6-state / 12-12 routes), honesty statement; `LINK_BUTTON_*` plain-`Link` buttons (no legacyBehavior) |
| Data-sources page at `/sources` | Verified | honest integration matrix (OSM road/facilities/community reports/deterministic model live; ML gated; gov/crowd/weather not connected) + live `/api/models/current` health check; sidebar entry |
| Streetlight lifecycle demo (`/civic`) | Verified | report → `REPORTED`; admin verify → `VERIFIED`; evidence counts/freshness/states update live; admin key from `safety-admin-key` localStorage; compose sets dev admin env |
| Safe-place finder (`/live`) | Verified | facilities within ~2 km of route destination via `fetchFacilitiesNear` bbox; ranked police/hospital/transit; "proximity, not a safety claim" footnote |
| Journey summary timeline | Verified | ended session timeline (started → last check-in → arrived/ended) + honest escalation notice ("stage reached" vs "never notified") |
| Backend is sole source of truth (no invented safety data) | Verified | `lib/api.ts` adapters; dead `fetchSegmentsByArea` (nonexistent endpoint) removed |
| Evidence adapter (coverage `null`, honest tiering) | Verified | typecheck + build green |
| Crowd honesty (value + wording) | Verified | `crowd: null` renders "not available — we never guess it" |
| Coverage honesty (Delhi-only chips) | Verified | live map chip + insights subtitle |
| Labels: "Plan Route", "Map", "Recent Incident Reports" | Verified | no "Live"/"Find Safe Route"/"Live Alerts" claims remain |
| Privacy settings page (real API, no react-redux) | Verified | typecheck/lint/build green |
| Privacy dashboard endpoint | Verified | `/api/privacy/dashboard` surfaced in privacy center (sharing, guardian, emergency, voice, discreet state) |
| Voice guidance UI | Verified | `VoiceGuidanceCard` on live page — start/stop/status via `/api/voice/*`; API smoke voice/start|status|stop PASS |
| Compare drawer: confidence + risk-band + evidence link | Verified | real `confidence` / `high_risk_fraction` / `estimated_safety` columns per route; OSM evidence link |
| Map alerts layer + 3D risk legend | Verified | `/api/alerts` markers (severity diamonds, popups) with filter toggle; 3D view shows per-segment risk legend ("from available evidence — not a guarantee") |

## 7. Data retention (Group 24)

| Data | Retention | Notes |
| --- | --- | --- |
| Evidence observations + history tables | Append-only, no purge | history triggers mirror every change; immutable VERIFIED/REJECTED |
| Reports (descriptions) | As long as the observation lives | redacted, encrypted at rest; re-encryption on key rotation is a manual migration |
| Report images | As long as the report lives | Fernet-encrypted; key is `REPORT_ENCRYPTION_KEY` (prod) or `.report_encryption_key` (dev) |
| Emergency / sharing / guardian sessions | Until ended or TTL | sharing auto-expires (30 min default cap); expired rows remain for audit |
| Device sessions (auth tokens) | 30 days TTL, then rejected | rows are never deleted automatically (audit); token hash only |
| Notification events | Append-only | in-app history |
| Admin audit trail | Append-only | hashed admin key, never raw |
| Redis rate-limit counters | Sliding window | ephemeral |

No automatic deletion policy exists for historical safety data (needed for
evidence history — directive: preserve evidence history). Deleting old
observations is intentionally a manual, audited operation.

## 8. Dependencies / production blockers

- **PostGIS reachable** — everything degrades to labeled demo data otherwise.
- **OSRM graph** — Delhi/Northern-Zone extract only; India-wide needs the full PBF + rebuild.
- **SMS/Telegram provider** — without one, SOS notifications are in-app only (honest). Telegram is now wired (`TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` + `NOTIFY_CHANNEL=telegram`) and records real `sent`/`failed`; SMS has no provider.
- **Admin key** — set `ADMIN_KEY` (and `ADMIN_DEV_KEY_ENABLED=0`).
- **`REPORT_ENCRYPTION_KEY`** — required outside development; fallback is random + persisted.
- **`TRUST_PROXY=1`** — only if the API sits behind a reverse proxy that
  strips client-supplied `X-Forwarded-For`.
- **CORS** — set `CORS_ORIGINS` to the real web origin.
- **Load testing** — not performed; no production-scale benchmarks.

## 9. Test totals (all green, 2026-08-16)

- **228 Python tests** pass (`apps/api`): 197 baseline + 9 security + 8 auth
  + 3 observability + emergency rate limits + facilities + journey/voice/privacy suites.
  Note: `test_auth.py` overrides the Redis-backed auth limiter with an
  in-memory limiter so the suite stays deterministic when Redis is reachable.
- **231 Python tests** pass (`apps/api`, after Telegram delivery tests): 228 above + 3 new (`test_telegram_channel_requires_both_credentials`, `test_telegram_unconfigured_status_is_no_channel`, `test_sms_channel_is_queued_not_sent`).
- Frontend: `tsc --noEmit`, Biome lint, `next build` all green.
- Web routes: 13/13 pages + `/manifest.webmanifest` + `/sw.js` + `/icon.svg` all 200 (/, /live, /insights, /civic, /sources, /community, /alerts, /report, /contacts, /admin, /profile, /settings, /privacy).
- E2E (needs the stack running): `e2e/verify.js` (26 checks), `e2e/verify-extra.js` (8), `e2e/theme-check.js`; live API smoke script 34/34 (auth, routes, preferences, discreet-mode, privacy, voice, fake-call, journey, community, contacts, notifications, revoke).