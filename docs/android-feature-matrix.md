# Android app — feature parity matrix

Web app: `apps/web` · API: `apps/api` · Android app: `android/`

Parity levels:
- **Full** — same user-facing capability as the web app, same backend contract.
- **Partial** — capability exists with a documented scope difference.
- **Web-only** — intentionally not in the Android app (justified per row).

| # | Feature group (web) | Web surface | Android implementation | Parity |
|---|--------------------|-------------|------------------------|--------|
| A | Home / live map | `/` RoutePlanner + MapView + MapFiltersBar | `HomeScreen` + `SafetyMap` (OSMDroid): search (backend geocode), plan route, map layers (incidents, lighting, heatmap, facilities, alerts, safety areas), location states (permission/GPS/accuracy/stale/timeout) | Full |
| B | Route planning & comparison | RoutePlanner, RouteCard, RouteComparisonDrawer, TransportSelector | `RouteViewModel` fetches `POST /api/routes`; 3 ranked cards (Safety Priority / Balanced / Time Priority) with backend values only; selection syncs map polyline; comparison; transport modes walking/driving/cycling | Full |
| C | Evidence | EvidenceDrawer, FreshnessBadge | `EvidenceSheet` per segment via `GET /api/segments/{id}/evidence`: by-type counts, score, freshness, confidence, conflicts, source counts, honest "no data" when zero observations | Full |
| D | Auth (device sessions) | lib/api.ts device-session flow | `AuthManager`: stable per-device client id, `POST /api/auth/device`, bearer on every call, transparent re-auth on 401, token in EncryptedSharedPreferences | Full |
| E | Anonymous reporting | `/report` | `ReportScreen` (categories, description, optional photo -> base64, segment attach from last planned route) + `QuickReportSheet` (1-tap, category + current location). Duplicate (409) and rate-limit (429) surfaced honestly | Full |
| F | ML / model info | backend `/api/models/current` | Read-only model version display in Settings; ML stays backend-only (gate untouched) | Partial |
| G | Overlays / heatmap | MapFiltersBar, SafetyHeatmapPanel | `SafetyMap` layers: incidents, lighting, facilities, alerts, safety areas, heatmap (backend cells only; crowd is never guessed) | Full |
| H | Safety alerts | `/alerts`, LiveAlertsList | `AlertsScreen`: `GET /api/alerts` real data only, severity / evidence-status / freshness / confidence, honest empty state | Full |
| I | Community | `/community`, CommunityFeed | `CommunityScreen`: feed (PENDING/VERIFIED/REJECTED from backend), create post; moderation stays web/admin-only | Full |
| J | Nearby facilities | `/civic` | `FacilitiesScreen`: `GET /api/facilities` bbox (police / hospital / pharmacy / fire / bus / metro / shelter), call / navigate intents, honest distance ("—" when unknown) | Full |
| K | Safety alerts (create) | web admin creates alerts | Alerts are created by the backend/admin only; app reads. Verified alerts may trigger an Android notification | Partial |
| L | Admin review | `/admin` | Web-only: admin key handling must not be embedded in a consumer APK (secret-in-APK rule) | Web-only |
| M | Privacy center | `/privacy` | `PrivacyScreen`: dashboard (`GET /api/privacy/dashboard`) with honest "unknown" values, settings toggles (voice guidance, discreet mode, language) | Full |
| N | Observability / rate limits | api access-log middleware | Client shows rate-limit (429) and server errors honestly; request ids are backend-side | Partial |
| O | Emergency / SOS | `/live` EmergencyCard + SOSConfirmation + EmergencyStatus | `SosScreen`: press-and-hold + countdown (3–5 s, cancellable), then `POST /api/emergency/sessions`; live status (notify_status, location sharing), location updates via foreground service, end with reason | Full |
| P | Trusted contacts | `/contacts` | `ContactsScreen`: CRUD via `/api/contacts`, role primary/secondary, enabled toggle, encrypted at rest (backend), honest empty state | Full |
| Q | Safety preferences | privacy settings (partial) + backend `/api/preferences` | `PreferencesScreen`: full preference set (better-lit, main roads, near emergency, avoid hazards/isolated, minimize walking, default profile, discreet, voice) — PUT only on explicit save | Full |
| R | Location sharing | `/live` LocationSharing | `SharingScreen`: start with TTL + recipients, live status, stop; foreground service keeps it honest while active | Full |
| S | Discreet mode | privacy settings (toggle) | `DiscreetScreen` + discreet launcher surface: settings from `/api/discreet-mode`, quick SOS gesture (triple-tap), neutral-app exit | Full |
| T | Fake call | backend `/api/fake-call` (no web UI) | `FakeCallScreen`: schedule call via backend session + local incoming-call screen when due (in-app, like the browser) | Partial |
| U | Voice guidance | privacy setting + backend `/api/voice/*` | `VoiceGuidance` (Android TTS, en/hi) started on route start; session tracked via `/api/voice/start|stop|status` | Full |
| V | Notifications | NotificationsBell | `NotificationsScreen` (in-app feed from `/api/notifications`) + Android notifications only for confirmed backend events (safety alert, check-in reminder, escalation) | Partial |
| W | Guardian journey | `/live` GuardianMode | `GuardianScreen`: start with guardian contacts + ETA + planned geometry, active status (deadline, deviation, escalation stages), check-in, end (arrived/cancelled) | Full |
| X | Journey check-ins | GuardianMode (destination/timed/custom) | `CheckinScreen`: `POST /api/journey/checkins` (destination, expected arrival, interval, grace, contacts), check-in / end, missed state from backend escalation | Full |
| Y | Deviation detection | GuardianMode | Deviation is computed backend-side against owner-provided geometry; app renders `deviation_detected` + first_deviation_at and notifies user | Full |
| Z | Offline / network states | web error handling | Every screen: Loading / Success / Empty / Error / Offline states; offline banner from ConnectivityManager; no fabricated data when offline — honest retry | Full |
| AA | Education / resources | none in web | Minimal `ResourcesScreen`: helplines (112/1091/181) with ACTION_DIAL intents; honest note that live data requires the backend | N/A (new) |
| AB | Onboarding | none in web | Minimal first-run onboarding explaining permissions (location, notifications) before use; skippable | N/A (new) |
| AC | Accessibility | web ARIA/touch targets | TalkBack-friendly content descriptions, 48 dp touch targets, large text support, not color-only (safety labels also carry text) | Full |
| AD | Performance | web clustering/debounce | Map overlays limited to bbox queries (<=500 items), lazy lists, debounced search, request cancellation on screen exit | Full |
| AE | Security | no secrets in client, bearer auth, no PII logging | Same: no API keys in APK (OSM tiles, no Google key), token in encrypted prefs, no location/contact logging | Full |
| AF | Language | English only web | English (default) + Hindi resources (values-hi) for key screens | Partial |
| AG | Offline emergency mode | none in web | Sparse: SOS retries with backoff when offline and surfaces helpline dialer as fallback (no fake "sent" state) | N/A (new) |

Non-negotiable rules carried over: no fabricated data, no boolean "safe" claims, uncertainty shown when evidence is weak, reporter identity never requested, ML untouched, backend is the single source of truth, safety never guaranteed.