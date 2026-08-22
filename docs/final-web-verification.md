# MAP FOR WOMEN — FINAL WEB VERIFICATION REPORT

**Date:** 2026-08-16
**Scope:** Final web completion pass — voice guidance UI, privacy dashboard, compare-drawer columns, honest copy, and end-to-end verification against the live compose stack.
**Result:** All five tasks complete and verified. API smoke 34/34 PASS. Web 12/12 routes 200 with content markers. Lint/typecheck/build green.

---

## 1. Tasks Completed

| # | Task | Status | Verification |
|---|---|---|---|
| 1 | Voice guidance UI on live page | Done | `VoiceGuidanceCard` start/stop/status wired to `/api/voice/start\|stop\|status`; API smoke voice/start, voice/status, voice/stop all PASS |
| 2 | Privacy dashboard surfaced in privacy center | Done | `/api/privacy/dashboard` rendered (location sharing, guardian, emergency, voice, discreet state); privacy/dashboard smoke PASS |
| 3 | Compare drawer: confidence + risk-band + evidence-link columns | Done | Drawer renders real `confidence`, `high_risk_fraction`, `estimated_safety`, and OSM evidence link per route; `/api/routes` responses verified to carry confidence (0.2602) and high_risk_fraction (0.0) |
| 4 | Honest copy on community page | Done | No fabricated authors/likes/comments; posts start PENDING with "submitted for review" messaging; community POST smoke PASS |
| 5 | E2E smoke (API + web) | Done | API 34/34 PASS against live stack; web 12/12 routes 200 |
| 6 | Alerts layer on map + 3D risk legend (TODO Phase 3 optional item) | Done | `MapCanvas` renders `/api/alerts` markers (severity-colored diamonds, popups with time-ago + source) behind an "Alerts" filter toggle; 3D view shows a per-segment risk legend ("From available evidence — not a guarantee"). Web rebuilt; /live, /alerts, /insights all 200; lint/typecheck/build green |

## 2. Files Changed

| File | Change |
|---|---|
| `apps/web/app/settings/page.tsx` | Discreet-mode save sends merged full object (backend requires all 5 fields) instead of partial patch |
| `apps/web/app/components/map/MapCanvas.tsx` | New `alerts` prop + alert marker layer (severity diamond icons, popups), `alerts` filter key in `MapFilters` |
| `apps/web/app/components/map/MapView.tsx` | Passes `alerts` through; `alerts: true` default filter; 3D-mode per-segment risk legend overlay |
| `apps/web/app/components/map/MapFiltersBar.tsx` | "Alerts" filter toggle (Bell icon) |
| `apps/web/app/globals.css` | `.alert-marker-*` severity styles + `.risk-legend-*` swatches |
| `apps/web/app/live/page.tsx` | Fetches `fetchAlerts()` and passes to `MapView`; demo-data chip also considers alert sources |
| `apps/api/app/api/preferences.py` | Added `SafetyPreferencesStore` + `client_hash` imports (fixes FastAPI dep degradation to query param) |
| `apps/api/app/api/discreet_mode.py` | Added `DiscreetModeSettingsStore` + `client_hash` imports |
| `apps/api/app/api/voice_guidance.py` | Added `VoiceGuidanceStore` + `client_hash` imports; `ended_at=None` on start response; `started_at` on stop response |
| `apps/api/app/api/guardian.py` | Added `JourneyCheckinStore`/`JourneyCheckinSession` imports; defined missing `_journey_checkin_response` helper; removed `journey_cancelled` notification (DB check violation) — `journey_completed` recorded only when reason is `arrived` |
| `apps/api/app/safety/preferences.py` | `update_preferences` — SELECT moved inside `with self._engine.begin()` block (fixes "This Connection is closed") |
| `apps/api/app/safety/discreet_mode.py` | `update_settings` — SELECT moved inside `with` block (same fix) |
| `TODO_WEB.md` | All five tasks + Phase 3 alerts/legend item + Phase 9 verification marked `[x]` |

## 3. Files Created

| File | Purpose |
|---|---|
| `apps/web/app/components/emergency/VoiceGuidanceCard.tsx` | Voice guidance start/stop/status UI (created in prior task step; verified this pass) |
| `apps/web/app/privacy/page.tsx` dashboard section | Privacy dashboard card (prior task step; verified this pass) |
| `apps/web/app/components/routes/RouteComparisonDrawer.tsx` columns | Confidence/risk-band/evidence-link columns (prior task step; verified this pass) |
| `C:\Users\legion\AppData\Local\Temp\opencode\api-smoke.ps1` | E2E API smoke script (34 checks) — smoke4.log run result: TOTAL 34 PASS 34 FAIL 0 |

## 4. API Endpoints Used (all verified live)

`GET /health`, `POST /api/auth/device`, `POST /api/auth/revoke`, `POST /api/routes`, `GET/PUT /api/preferences`, `GET/PUT /api/discreet-mode`, `GET /api/privacy/settings`, `GET /api/privacy/dashboard`, `POST /api/voice/start`, `GET /api/voice/status`, `POST /api/voice/stop`, `POST /api/fake-call`, `GET /api/fake-call/{id}`, `POST /api/journey/checkins`, `GET /api/journey/checkins/active`, `POST /api/journey/checkins/{id}/checkin`, `POST /api/journey/checkins/{id}/end`, `POST /api/community`, `GET /api/contacts`, `GET /api/notifications`.

## 5. Backend Changes (integration-blocker fixes, minimal, justified)

Backend code was only touched after each issue was proven to be a real integration blocker by live API smoke:

1. **FastAPI dependency degradation (422 "store" query param)** — `from __future__ import annotations` + missing store TYPE imports caused `get_type_hints` NameError, silently demoting the dependency to a query param. `preferences.py`, `discreet_mode.py`, `voice_guidance.py` were missing their store-type imports (`privacy.py` worked because it imports them). Fixed by importing the store types.
2. **`client_hash` NameError** in `preferences.py`/`discreet_mode.py`/`voice_guidance.py` — `_require_limit` references it without import. Fixed with `from app.identity import client_hash`.
3. **`guardian.py` missing `JourneyCheckinStore` import** — fixed.
4. **ResourceClosedError "This Connection is closed"** — post-write SELECT executed after the `with self._engine.begin()` block closed the connection (`preferences.py`, `discreet_mode.py`). Fixed by moving the SELECT inside the block.
5. **`NameError: _journey_checkin_response`** in `guardian.py` — helper never defined. Added it mapping session → `JourneyCheckinResponse` (all fields).
6. **voice/start 500** — `VoiceGuidanceResponse` requires `ended_at`. Fixed with `ended_at=None`.
7. **voice/stop 500** — response required `started_at`. Added from session.
8. **journey end 500 CheckViolation** — `notification_events_type_check`: `journey_cancelled` not in allowed types. Removed that record; `journey_completed` recorded only when reason = `arrived`. Allowed types: `sos_started, sos_ended, location_sharing_started, location_sharing_stopped, guardian_started, guardian_ended, journey_completed, checkin_reminder, checkin_missed, checkin_escalated, route_changed, safety_alert`.

## 6. Database Changes

- Applied canonical `apps/api/app/db/schema.sql` to the compose PostGIS container (idempotent; previously the DB had an older seeded schema missing `device_sessions`, `safety_preferences`, `discreet_mode_settings`, `voice_guidance_sessions`, `fake_call_sessions`, `journey_checkins`, `safety_alerts`, `notification_events`, etc.).
- One non-fatal ERROR during apply: partial index `idx_safety_alerts_active` (`WHERE expires_at > now()`) — `now()` is not immutable, index not created. Not a blocker (queries do not depend on it).
- No other schema changes.

## 7. E2E Results

**API smoke (live stack, smoke4.log):** TOTAL 34 · PASS 34 · FAIL 0
- Auth: device issue, revoke, and 401-after-revoke all correct
- Routing: all 3 profiles return real OSRM data (distance 2842.2 m, risk 0.0223, safety 98, confidence 0.26, model `deterministic-baseline-v1`)
- Preferences / discreet-mode GET+PUT round-trips; privacy settings + dashboard
- Voice start/status/stop (session lifecycle with started_at/ended_at)
- Fake call create/status; journey create/active/checkin/end; community POST (PENDING); contacts; notifications
- Progression across passes: 22/29 → 26/31 → 32/34 → **34/34**

**Web pages (live :3000):** all 12 routes 200 — `/`, `/live`, `/insights`, `/alerts`, `/community`, `/report`, `/settings`, `/profile`, `/privacy`, `/civic`, `/contacts`, `/admin` — each with its own content marker present. The only "hydration" marker match is `suppressHydrationWarning` (standard Next.js attribute), not an error.

**Container state:** api, osrm, postgis, redis healthy; web up. `docker compose logs web --since 30m` — no errors.

## 8. Build Results

| Check | Command | Result |
|---|---|---|
| Lint | `pnpm lint` (Biome, `biome check .`) | Clean — 76 files checked, no fixes applied |
| Typecheck | `pnpm typecheck` (`tsc --noEmit`) | Clean |
| Build | `pnpm build` (Next 16) | ✓ Compiled successfully; all 12 routes statically prerendered |

## 9. Console Results

- API container logs during smoke: no 5xx other than the deliberately-exercised 401 (auth-revoke check) and 404 (voice stop without session contract).
- Web container logs: no errors in the last 30 minutes.
- Browser console: **NOT VERIFIED** — no browser automation available (see Known Limitations).

## 10. Docker Results

| Service | Status |
|---|---|
| api | Up (healthy) — rebuilt after backend fixes |
| osrm | Up (healthy) |
| postgis | Up (healthy) |
| redis | Up (healthy) |
| web | Up |

## 11. Mobile Results

**NOT VERIFIED** — no device/browser automation available. `MobileNav` and responsive shell are implemented, but mobile viewport behavior was not exercised this pass. The API smoke covers the same endpoints the mobile shell calls.

## 12. Accessibility Results

**NOT VERIFIED this pass** — no automated a11y scan run (no browser automation). Prior passes maintained `:focus-visible`, `prefers-reduced-motion`, and semantic labels per design.md; no new a11y regressions are known. Honest disclaimer: not re-verified.

## 13. Known Limitations

- No browser automation → browser console, hydration, mobile viewport, and accessibility checks are code-inspection only.
- Partial index `idx_safety_alerts_active` absent (non-immutable `now()` predicate) — non-blocking.
- `POST /api/reports/quick` remains unwired in the web UI (backend exists).
- OSRM covers Northern-Zone/Delhi extract only; ML gate closed by design (no trained model — never claimed).
- Community moderation has no dedicated UI (SQL/admin API only).

## 14. Backend Blockers

**None remaining.** Every blocker found during this pass (dependency degradation, missing imports, connection-closed, missing response fields, notification check violation) was fixed and verified via 34/34 smoke PASS. No fabricated data, no `safe=true`, no guarantees anywhere.

## 15. TODO_WEB.md Status

**COMPLETE.** All five final tasks, the Phase 3 alerts-layer/3D-legend item, and Phase 9 verification are `[x]` (verified with real backend wiring); a "Final status (2026-08-16)" block was added at the top of `TODO_WEB.md`. No `[-]` items remain. Honest gaps outside web scope: `POST /api/reports/quick` unwired in the UI, OSRM Northern-Zone only, ML gate closed by design, community moderation SQL/admin-only.

---

*Report generated 2026-08-16. All numbers come from recorded smoke logs and live container checks — nothing invented.*