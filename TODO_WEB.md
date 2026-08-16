# MAP FOR WOMEN — COMPLETE WEB PLATFORM

Task owner: assistant (web only — `apps/web`). Backend is authoritative; never fabricate data.

## Final status (2026-08-16)
**COMPLETE** — all phases and optional items are `[x]` (verified complete: inspected code + real backend wiring).
- Lint / typecheck / build green; API smoke 34/34; web 12/12 routes 200.
- Remaining known gaps (honest, outside web scope): `POST /api/reports/quick` unwired in the UI; OSRM Northern-Zone only; ML gate closed by design; community moderation via SQL/admin API only.
- Full details: `docs/final-web-verification.md`.

## Status legend
- `[x]` verified complete (inspected code; real backend wiring)
- `[-]` partial / needs work
- `[ ]` not started
- `[~]` in progress
- `[!]` blocked or violates a rule

---

## Phase 0 — Discovery
- [x] Inventory the entire `apps/web` surface (pages, components, lib, config)
- [x] Map every backend endpoint used / unused by the frontend
- [x] Audit for fabricated data, fake personas, dead code, broken links
- [x] Write this discovery report + `TODO_WEB.md`
- [x] STOP — no application code changes in this phase

---

## Phase 1 — Shell, navigation & design system
- [x] `app/layout.tsx` root layout + no-FOUC theme init script
- [x] `AppShell.tsx` — SOS context, active-emergency restore
- [x] `Sidebar.tsx` — nav (live, insights, alerts, report, contacts, community, civic, admin), emergency button
- [x] `Sidebar.tsx:25` — hardcoded `badge: 4` on Alerts removed → real count from `/api/alerts` (null badge when fetch fails)
- [x] `MobileNav.tsx` — 5 tabs (Map / Insights / SOS / Alerts / Report)
- [x] `TopHeader.tsx:115-129` — fake persona "Ananya Sharma, Verified User" replaced with pseudonymous "This device / Pseudonymous profile" chip → `/profile`
- [x] `Sidebar.tsx` — `/profile` and `/settings` links now resolve (pages created in Phase 7); Privacy Center link added
- [x] UI kit — Button, Card, Badge, Modal, Drawer, Input, Select, Progress, Pill, Tabs, Tooltip, Skeleton, Avatar, Gauge, Chart, Dropdown, IconButton
- [x] Theme (ThemeProvider / ThemeToggle) + motion primitives (Reveal, Tilt, PageTransition)
- [x] Alerts badge count from `/api/alerts` — replaces `badge: 4`

## Phase 2 — Route planner & routing UX
- [x] `RoutePlanner.tsx` — origin/destination, geocode debounce (`/api/geocode`), voice input (en/hi), use-my-location, transport selector, night simulation
- [x] `RoutePlanner.tsx` — static `PLACE_SUGGESTIONS` fallback (real Delhi landmarks, real coords; used only as geocode fallback) — acceptable, keep
- [x] `live/page.tsx` — calls `POST /api/routes`, adapts results (lon/lat flip), stores `mf:last-route-segments`
- [x] `live/page.tsx:181` — `safety_preference: "safety"` hardcoded → `PreferenceSelector` (balanced/safety/time) wired, defaults from `GET /api/preferences`
- [x] `RouteCard.tsx` — label styling, FreshnessBadge, confidence, uncertainty, high-risk share, risky exposure
- [x] `RouteComparisonDrawer.tsx` — safety/distance/duration compare, honest disclaimer
- [x] Compare drawer: confidence + risk-band + evidence-link columns (real `confidence`/`high_risk_fraction` from `/api/routes`; OSM evidence link)
- [x] `ShareTrip` (`live/page.tsx:53`) uses Google Maps → now OpenStreetMap directions link + share

## Phase 3 — Map & overlays (Leaflet + OSM, never Google Maps)
- [x] `MapCanvas.tsx` — Leaflet init, CARTO/OSM dark tiles, marker clustering, per-segment risk-colored polylines, tooltips
- [x] `MapView.tsx` — filters bar, 2D/3D toggle, zoom controls, attribution
- [x] `MapFiltersBar.tsx` — incidents / lighting / facilities / heatmap toggles
- [x] `MapCanvas.tsx:360` — facility tooltip null-guarded ("distance unknown" when `distance_m` is null)
- [x] Incident popups (timeAgo + source), lighting markers (working/uncertain/out), heat circles
- [x] Alerts layer from `/api/alerts` (severity-colored diamond markers, popups, filter toggle) + per-segment risk legend in 3D view (honest "from available evidence — not a guarantee")

## Phase 4 — Safety scores, evidence & transparency
- [x] `lib/score.ts` — bands, confidence levels, risk→score conversion, honest wording (`RECOMMENDED_WORDING`)
- [x] `lib/format.ts` — duration/distance/time-ago/freshness tiers
- [x] `lib/adapt.ts` — RouteResult adapter; honest "unknown" freshness when backend lacks it
- [x] `SafetyScoreCard.tsx`, `ScoreTrendCard.tsx` (by-time-of-day chart), `FreshnessBadge.tsx`
- [x] `lib/api.ts` `fetchSegmentEvidence` — maps `GET /api/segments/{id}/evidence` (sources, conflicts, freshness, model_version; coverage stays null — never invented)
- [x] `EvidenceDrawer.tsx` wired — "WHY THIS SCORE?" on `SafetyScoreCard` (live page), opens evidence drawer
- [x] `/api/models/current` surfaced — model version, dataset versions, ML-gate state in evidence drawer (traceability)
- [x] Insights page: area safety, heatmap zones, comparisons table, "What the evidence says" honest copy

## Phase 5 — Emergency, guardian, location sharing & notifications
- [x] `EmergencyCard` → `SOSConfirmation` (helplines, 5s countdown, location required, restore active session)
- [x] `EmergencyStatus` — honest `notify_status` labels ("No channel configured — NOT notified automatically")
- [x] `LocationSharing` — opt-in, 30-min TTL, live watchPosition → `updateSharingLocation`, auto-expiry countdown
- [x] `GuardianMode` — contacts picker, ETA, planned-geometry monitoring, 15s poll, check-in, end (arrived/cancelled), honest escalation copy
- [x] `NotificationsBell` — real `/api/notifications` feed with delivery-status honesty
- [x] Journey check-ins — `JourneyCheckinCard` (start/check-in/end, contacts picker, ETA, 15s poll) on live page
- [x] Fake-call feature — `FakeCallCard` (caller name, trigger, status badge, 10s poll) on live page

## Phase 6 — Community, reports & alerts
- [x] `ReportPage` — category select, description, optional image (3.5 MB cap, EXIF-stripped), attaches to last planned segment, anonymous
- [x] Alerts page — real `/api/alerts`, severity/category filters
- [x] Community feed — reads `GET /api/community` (contract mismatch fixed: unwraps `{posts}`), anonymous cards (no invented author/likes/comments)
- [x] `community/page.tsx` — "Post update" wired to real `POST /api/community`; posts start PENDING, honest "submitted for review" messaging + errors

## Phase 7 — Privacy, settings & profile
- [x] `privacy/page.tsx` — privacy center: location sharing, guardian, emergency sessions, contacts, settings (voice guidance, discreet mode, voice language) via `/api/privacy/settings`
- [x] `settings/page.tsx` — route preferences (default profile + toggles → `PUT /api/preferences`), discreet mode (`PUT /api/discreet-mode`), voice guidance
- [x] `profile/page.tsx` — pseudonymous device identity (`lib/client-id.ts`), session revoke via `POST /api/auth/revoke` (clears local identity)
- [x] Discreet-mode UI: `DiscreetModeProvider` in AppShell masks sidebar brand + tab title with neutral label/icon from `/api/discreet-mode`
- [x] Voice guidance: `VoiceGuidanceCard` on live page — start/stop/status wired to `/api/voice/start|stop|status` (started_at/ended_at shown, active-state polling, honest copy)
- [x] `/api/privacy/dashboard` surfaced in privacy center (location sharing, guardian, emergency, voice, discreet state)

## Phase 8 — Admin & civic operations
- [x] `admin/page.tsx` — key-gated review queue, verify/reject (sticky, audited)
- [x] `civic/page.tsx` — streetlight failure worklist, incident categories, priority areas (real data)
- [x] `civic/page.tsx:14` — `mapsUrl()` now OpenStreetMap (`mlat/mlon#map=19/...`), never Google Maps

## Phase 9 — Verification & polish
- [x] `pnpm lint` (Biome) clean
- [x] `pnpm typecheck` (`tsc --noEmit`) clean
- [x] `pnpm build` (Next 16) green — read `node_modules/next/dist/docs/` before touching any code
- [x] Re-audit honest copy: no guarantees, no invented numbers, demo chips everywhere demo data is used (community page copy fixed)
- [x] e2e smoke: API smoke 34/34 against running compose stack (auth, routes with risk/confidence, preferences, discreet-mode, privacy, voice, fake-call, journey check-in/end, community, contacts, notifications, revoke); web pages all 12 routes 200 with content markers

---

# Discovery report (Phase 0 output)

## 1. Feature inventory (verified)
| Area | Files | Status |
|---|---|---|
| Routing | `live/page.tsx`, `RoutePlanner`, `RouteCard`, `RouteComparisonDrawer`, `TransportSelector`, `PreferenceSelector` | Working; preference selector wired to `/api/preferences` |
| Map | `MapView`, `MapCanvas`, `MapControls`, `MapFiltersBar`, `MapModeToggle` | Working (Leaflet + CARTO/OSM); tooltip null-guarded |
| Safety scores | `SafetyScoreCard`, `ScoreTrendCard`, `FreshnessBadge`, `lib/score.ts` | Working; "Why this score?" wired |
| Evidence | `EvidenceDrawer`, `fetchSegmentEvidence` | **Wired** (live page + model traceability) |
| SOS | `EmergencyCard`, `SOSConfirmation`, `EmergencyStatus` | Working, honest |
| Guardian | `GuardianMode` (+ privacy center copy) | Working |
| Location sharing | `LocationSharing` (+ privacy center copy) | Working |
| Notifications | `NotificationsBell` | Working |
| Reports | `report/page.tsx` | Working (segment-attached) |
| Alerts | `alerts/page.tsx`, `LiveAlertsList` | Working; sidebar badge = real count |
| Community | `community/page.tsx`, `CommunityFeed` | Read + publish wired (`POST /api/community`, pending-review UX) |
| Fake call | `FakeCallCard` | Working (trigger + status poll) |
| Journey check-ins | `JourneyCheckinCard` | Working (start/check-in/end + contacts) |
| Privacy | `privacy/page.tsx` | Working |
| Settings | `settings/page.tsx` | New — route prefs, discreet mode, voice guidance |
| Profile | `profile/page.tsx` | New — pseudonymous identity + session revoke |
| Contacts | `contacts/page.tsx` | Working (full CRUD) |
| Admin | `admin/page.tsx` | Working |
| Civic | `civic/page.tsx` | Working; **OSM links** (was Google Maps) |

## 2. Backend endpoint coverage
- Wired: `/api/routes`, `/api/geocode`, `/api/segments/{id}/evidence`, `/api/incidents`, `/api/alerts`, `/api/lighting`, `/api/facilities`, `/api/safety/area`, `/api/safety/areas`, `/api/safety/heatmap`, `/api/community` (GET+POST), `/api/reports`, `/api/auth/device` + `/api/auth/revoke`, `/api/contacts` CRUD, `/api/emergency/sessions*`, `/api/location-sharing*`, `/api/guardian/sessions*`, `/api/notifications`, `/api/privacy/settings`, `/api/admin/reports*`, `GET/PUT /api/preferences`, `GET/PUT /api/discreet-mode`, `POST/GET /api/fake-call`, `/api/models/current`, `POST/GET /api/journey/checkins`.
- **NOT wired (backend exists):** `POST /api/reports/quick`.

## 3. Violations & bugs found (fix order)
1. ~~`Sidebar.tsx` hardcoded alerts badge `4`~~ — fixed: real `/api/alerts` count.
2. ~~`TopHeader.tsx` fake persona "Ananya Sharma"~~ — fixed: pseudonymous "This device" chip.
3. ~~`community/page.tsx` fake publish~~ — fixed: real `POST /api/community`, pending-review UX.
4. ~~Google Maps links (ShareTrip, civic mapsUrl)~~ — fixed: OSM only.
5. ~~`MapCanvas.tsx` facility tooltip "nullm away"~~ — fixed: "distance unknown" guard.
6. ~~`/settings`, `/profile` broken links~~ — fixed: pages created.
7. ~~`safety_preference` hardcoded~~ — fixed: PreferenceSelector wired to `/api/preferences`.
8. ~~Evidence drawer dead; no "WHY THIS SCORE?"~~ — fixed: wired to SafetyScoreCard with model traceability.

## 4. Design principles already respected (keep)
- Honest copy everywhere ("estimate, not a guarantee"; "no channel configured — NOT notified").
- Demo-data chip when `demo_seed` sources detected; offline banner.
- Confidence/freshness/uncertainty surfaced on every score.
- `NEXT_PUBLIC_USE_MOCK` dev-only; real API default.
- No guarantees; identity never shown; evidence history preserved.

## 5. Implementation order (per AGENTS.md coding order)
1. ~~Phase 1 shell fixes (badge, persona, broken links)~~ — done
2. ~~Phase 6 community POST fix (data loss today)~~ — done
3. ~~Phase 2/3 preference selector + OSM links + tooltip fix~~ — done
4. ~~Phase 4 evidence drawer wiring + model version~~ — done
5. ~~Phase 7 settings/profile pages + discreet mode + voice guidance clients~~ — done
6. ~~Phase 5 journey check-ins + fake call UI~~ — done
7. ~~Phase 9 verification (lint/typecheck/build green; e2e smoke)~~ — done: lint/typecheck/build green; API smoke 34/34; web 12/12 routes 200

## 6. Verified state of backend (prior session)
- Fake-call `scheduled_at` bug fixed (`schemas.py` optional field; `fake_call.py` default now UTC). `228 passed` in `apps/api`.