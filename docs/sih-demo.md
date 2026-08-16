# SIH demo script + alignment (generic women's-safety PS)

Demo is built to run on the judge's time budget (target: **7–8 minutes** total).
Every screen is reachable from `http://localhost:3000` on a laptop; the phone
(mobile viewport) shows the same app against the same API.

## Real numbers you can quote (no invented stats)

- 340 demo evidence observations seeded across 10 Delhi hotspots (harassment,
  suspicious activity, road hazards, streetlight failures, poor lighting), with
  verified and conflicting states, labeled `demo_seed` — the UI shows a
  "Demo data" badge whenever they appear.
- 231 API tests passing (incl. honest Telegram delivery status tests); live
  API smoke 34/34 (auth, routes, preferences, discreet-mode, privacy, voice,
  fake-call, journey, community, contacts, notifications, revoke); web 12/12
  routes 200; Biome lint + `tsc --noEmit` + `next build` green.
- Day → Night toggle changes real risk estimates: sample Connaught Place →
  India Gate walk risk 2.7% (day) → 5.4% (night) — the safer route changes.
- Entire stack runs in Docker; API degrades to the in-memory evidence snapshot
  if PostGIS is unreachable (offline-capable).

## Demo flow (run this exact order)

### 1. Landing on /live (45s)
- Map renders with incident + streetlight markers from `/api/incidents` and
  `/api/lighting` (demo data). Point out the **"Demo data"** badge — say plainly:
  *"This is illustrative data seeded for the demo; the system labels it so no
  one mistakes it for real incident records."*
- Right panel: area safety score for Connaught Place with evidence sources.

### 2. Plan a route — day (1m30s)
- Starting point: Connaught Place → Destination: Lajpat Nagar (or India Gate).
- Optional wow: tap the crosshair in "Starting point" to use live geolocation;
  or tap the mic and *speak the destination in Hindi* — say "इंडिया गेट".
- Transport: walking. Click **Find Safe Route**.
- 3 route cards appear (Safety Priority / Balanced / Time Priority) with scores,
  confidence, uncertainty, and the disclaimer *"not a safety guarantee"*.
- Click **Compare** → drawer shows route trade-offs. Pick the safety route.
- Note the risk heatmap layer over the map — toggle it with the "Heatmap" chip.
- New: the **"Riskier tonight" chip** replans the same trip at 22:00 IST through
  the real API and shows the honest model delta (e.g. CP → Saket: 1.4% → 2.6%).

### 3. The night toggle — the money shot (1m30s)
- In the planner, **Demo: simulate time → Night**, replan.
- Route scores drop and the recommended route changes because night-time
  evidence (lighting failures, harassment reports) is weighted higher.
- This is a demo flag the UI labels as such; production uses IST hour.

### 3b. Safe places near the destination (45s)
- With a route selected, the **Safe-place finder** lists facilities within
  ~2 km of the destination (police > hospital > transit first) from the live
  facilities API — with the honest footnote "proximity, not a safety claim".

### 4. Insights (1m)
- /insights: area safety 0–100, 7-day incidents, lighting evidence, hourly
  time-of-day curve, area risk map (heatmap), and a new **area comparison
  table** across all 10 monitored areas. All live from `/api/safety/*`.

### 4b. Data sources page (45s)
- /sources: honest integration matrix — OSM road network, facilities and
  community reports are **live**; the deterministic risk model is **live**;
  the ML pipeline is **gated behind validation**; gov/municipal feeds,
  crowd-sourced data and weather are **not connected** (no invented claims).
  Live API health check pings `/api/models/current` on load.

### 5. SOS + location share (1m)
- Open **Emergency SOS** → contacts (181 / 112 / 102).
- **Share live location** → browser geolocation, share/copy a maps link.
- Works on the phone view too — demonstrate the same flow on the phone browser.
- If a Telegram bot is configured (`NOTIFY_CHANNEL=telegram` +
  `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`), SOS events are actually sent and
  the notification list shows honest `sent`/`failed`. Without credentials the
  UI says `no_channel` — never fakes delivery.

### 6. Share trip (45s)
- With a route planned, **Share** builds an OpenStreetMap directions link (never
  Google Maps) + copies a trip link to the clipboard.

### 7. Report loop (1m)
- /report: describe an incident, pick type, submit. Backend validates, dedupes,
  and the observation flows into the evidence pipeline (model stays gated).

### 8. Civic Operations (1m30s)
- /civic: the same evidence becomes a municipal worklist — streetlight
  failures with "open in maps", incident categories for patrol planning, and
  priority areas ranked by estimated safety. This is the government/civic-body
  story judges ask about.
- **Streetlight lifecycle demo**: pick a segment from your last planned route →
  "Report streetlight failure" (becomes REPORTED, evidence count/freshness move
  live) → "Verify repair (municipality)" with the admin key → VERIFIED.
  The evidence numbers update on screen — a real end-to-end civic loop.

### 9. Review Queue + community moderation (45s)
- /admin: enter the dev admin key (`dev-admin-key`), see the report queue with
  Verify/Reject (sticky, audited). Below it, anonymous community posts are
  moderated — Verify/Reject applies a real status change the public feed
  reflects (PENDING + VERIFIED only).

### 10. Language toggle + PWA (30s)
- Top header: toggle **हिंदी / EN** — the sidebar, mobile nav, header, search
  placeholder and emergency card switch language instantly (persisted in
  `mf:lang`).
- The site is installable as a PWA (manifest + service worker; the worker
  caches static assets only and never `/api/` responses — stale safety data
  is never served).

### 11. Close (30s)
- One-line: *"The system never promises safety — it surfaces evidence,
  uncertainty, and routes. Civic bodies can action the lighting/incident data."*

## SIH alignment (keep this framing)

| SIH criterion | What we show |
| --- | --- |
| Problem relevance | Night-travel safety, last-mile risk, lighting + incident evidence |
| Innovation | Evidence engine (weighted, uncertainty-aware) instead of "AI vibe scores"; demo-labeled data; no fabricated accuracy |
| Tech depth | FastAPI + PostGIS routing, OSRM, offline snapshot fallback, 231 tests |
| Usability | 2-field planner, voice input (हिंदी/English), geolocation, mobile-first, SOS + share-trip, EN/हिंदी UI toggle, PWA installable, accessibility (focus traps, aria-live, labeled icons) |
| Impact | Streetlight failure data is actionable by municipalities (Civic Ops page); helpline numbers one-tap |
| Scalability | Plug other cities: replace OSM extract + evidence snapshot |

## Honesty guardrails (do not break these on stage)

- Never say the system *prevents* harassment or *guarantees* safety.
- Never claim the demo data is real. The badge exists for exactly this.
- If a judge asks about ML: our ML pipeline is **gated behind validation** and
  not used in routing decisions; evidence scoring is rule-based + transparent.

## Fully offline / air-gapped mode (judge's laptop without internet)

The entire demo works with no internet access. Everything needed runs in
Docker on the laptop (`docker compose up`) — API :8000, OSRM :5000, PostGIS
and Redis are local; the web app talks only to `localhost`.

- **Map tiles**: the app tries the CARTO tile CDN, and if tiles fail to load
  it degrades to a dark map surface — routes, risk coloring, markers and
  popups remain fully interactive. (Set `NEXT_PUBLIC_TILE_URL` to a local
  tile server for a richer offline map.)
- **Geocoding**: `/api/geocode` is a deterministic local gazetteer (facilities
  table + built-in area centers) — no external geocoder, no Nominatim.
- **Search fallback**: even with the API unreachable, the planner's datalist
  always includes 10 real Delhi landmarks (`PLACE_SUGGESTIONS`).
- **Voice input**: Chrome's Web Speech API needs Google servers, so offline it
  shows an honest "voice input needs an internet connection — type the place
  name instead" message; typed input is the primary flow anyway.
- **Fonts**: self-hosted at build time (`next/font/google`) — no font CDN at
  runtime.
- **External links**: OSM directions/maps links are user-initiated openers;
  the demo never depends on them rendering.
- **PWA service worker**: caches static assets only (build output, icons) and
  the app shell for offline reloads — `/api/` responses are never cached, so
  offline you always see the honest offline banner, never stale safety data.
- **A11y**: dialogs and drawers trap focus + restore it on close, Escape
  closes, the SOS countdown is `aria-live`-announced, icon buttons have
  labels, color is never the only signal (text + shape always accompany it).

If you want to *prove* air-gapped readiness on stage: unplug/disable Wi-Fi,
reload `localhost:3000`, plan Connaught Place → India Gate, and watch the map
degrade + routes still score. That is a strong reliability story for judges.
