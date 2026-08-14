# SIH demo script + alignment (generic women's-safety PS)

Demo is built to run on the judge's time budget (target: **7–8 minutes** total).
Every screen is reachable from `http://localhost:3000` on a laptop; the phone
(mobile viewport) shows the same app against the same API.

## Real numbers you can quote (no invented stats)

- 300 demo evidence observations seeded across 10 Delhi hotspots (harassment,
  suspicious activity, streetlight failures, poor lighting), labeled `demo_seed`
  — the UI shows a "Demo data" badge whenever they appear.
- 87 API tests passing; 24/24 UI E2E checks, 8/8 SOS/edge checks, theme checks.
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
- Transport: walking. Click **Find Safe Route**.
- 3 route cards appear (Safety Priority / Balanced / Time Priority) with scores,
  confidence, uncertainty, and the disclaimer *"not a safety guarantee"*.
- Click **Compare** → drawer shows route trade-offs. Pick the safety route.

### 3. The night toggle — the money shot (1m30s)
- In the planner, **Demo: simulate time → Night**, replan.
- Route scores drop and the recommended route changes because night-time
  evidence (lighting failures, harassment reports) is weighted higher.
- This is a demo flag the UI labels as such; production uses IST hour.

### 4. Insights (1m)
- /insights: area safety 0–100, 7-day incidents, lighting evidence, hourly
  time-of-day curve, area risk map (heatmap). All live from `/api/safety/*`.

### 5. SOS + location share (1m)
- Open **Emergency SOS** → contacts (181 / 112 / 102).
- **Share live location** → browser geolocation, share/copy a maps link.
- Works on the phone view too — demonstrate the same flow on the phone browser.

### 6. Share trip (45s)
- With a route planned, **Share** builds a Google Maps directions link.

### 7. Report loop (1m)
- /report: describe an incident, pick type, submit. Backend validates, dedupes,
  and the observation flows into the evidence pipeline (model stays gated).

### 8. Close (30s)
- One-line: *"The system never promises safety — it surfaces evidence,
  uncertainty, and routes. Civic bodies can action the lighting/incident data."*

## SIH alignment (keep this framing)

| SIH criterion | What we show |
| --- | --- |
| Problem relevance | Night-travel safety, last-mile risk, lighting + incident evidence |
| Innovation | Evidence engine (weighted, uncertainty-aware) instead of "AI vibe scores"; demo-labeled data; no fabricated accuracy |
| Tech depth | FastAPI + PostGIS routing, OSRM, offline snapshot fallback, 87 tests |
| Usability | 2-field planner, mobile-first, SOS + share-trip, accessibility labels |
| Impact | Streetlight failure data is actionable by municipalities; helpline numbers one-tap |
| Scalability | Plug other cities: replace OSM extract + evidence snapshot |

## Honesty guardrails (do not break these on stage)

- Never say the system *prevents* harassment or *guarantees* safety.
- Never claim the demo data is real. The badge exists for exactly this.
- If a judge asks about ML: our ML pipeline is **gated behind validation** and
  not used in routing decisions; evidence scoring is rule-based + transparent.
