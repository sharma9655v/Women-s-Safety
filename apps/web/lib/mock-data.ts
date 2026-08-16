import { scoreFromRisk } from "./score";
import type {
  AdminReport,
  AreaSafety,
  CommunityPost,
  Facility,
  GeocodeResult,
  Incident,
  LightingObservation,
  RouteCandidate,
} from "./types";

/**
 * DEMO DATA — typed exactly like the FastAPI contracts.
 * Flip NEXT_PUBLIC_USE_MOCK=false and point NEXT_PUBLIC_API_URL at the
 * backend; the components consume identical shapes.
 */

const INDIA_GATE: [number, number] = [28.6129, 77.2295];
const AKSHARDHAM: [number, number] = [28.6129, 77.2772];

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/** Build a deterministic polyline with a couple of bends. */
function buildGeometry(
  from: [number, number],
  to: [number, number],
  bend: [number, number][],
  seed: number,
): [number, number][] {
  const points: [number, number][] = [];
  const stops = [from, ...bend, to];
  const samples = 40;
  for (let i = 0; i < samples; i += 1) {
    const t = i / (samples - 1);
    const seg = Math.min(stops.length - 2, Math.floor(t * (stops.length - 1)));
    const local = t * (stops.length - 1) - seg;
    const a = stops[seg];
    const b = stops[seg + 1];
    const wobble =
      ((Math.sin(t * 40 + seed) * 0.5 + Math.sin(t * 17 + seed * 2) * 0.5) * 0.0009) /
      Math.max(1, seg + 1);
    points.push([lerp(a[0], b[0], local) + wobble, lerp(a[1], b[1], local) + wobble]);
  }
  return points;
}

function riskColorsFor(riskSegs: number[]): string[] {
  const colors: string[] = [];
  for (let i = 0; i < 40; i += 1) {
    const r = riskSegs[Math.min(riskSegs.length - 1, Math.floor((i / 40) * riskSegs.length))];
    colors.push(r < 0.04 ? "#22c55e" : r < 0.12 ? "#f59e0b" : "#f43f5e");
  }
  return colors;
}

const SAFETY_NORTH: number[] = Array.from(
  { length: 40 },
  (_, i) => 0.03 + 0.05 * Math.abs(Math.sin(i * 0.55)),
);
const SAFETY_MID: number[] = Array.from(
  { length: 40 },
  (_, i) => 0.05 + 0.1 * Math.abs(Math.sin(i * 0.7 + 1.2)),
);
const SAFETY_SHORT: number[] = Array.from(
  { length: 40 },
  (_, i) => 0.02 + 0.22 * Math.abs(Math.sin(i * 0.9 + 0.4)),
);

export const MOCK_ROUTE_CANDIDATES: RouteCandidate[] = [
  {
    id: "rec-1",
    label: "recommended",
    title: "Recommended",
    via: "via Tilak Marg",
    distance_m: 11200,
    duration_s: 28 * 60,
    safety: {
      value: 78,
      band: "high",
      confidence: "medium",
      evidence: {
        sources: [],
        confidence: "medium",
        confidence_value: 0.58,
        freshness: {
          tier: "fresh",
          label: "Fresh",
          updated_at: new Date(Date.now() - 10 * 60_000).toISOString(),
          detail: "Updated recently",
        },
        conflicts: [],
        coverage: 0.72,
      },
    },
    indicators: ["Well Lit", "Low Crowd", "Good Roads"],
    route_type: "safety_priority",
    geometry: {
      type: "LineString",
      coordinates: buildGeometry(
        INDIA_GATE,
        AKSHARDHAM,
        [
          [28.62, 77.246],
          [28.615, 77.26],
        ],
        1,
      ),
    },
    risk_colors: riskColorsFor(SAFETY_NORTH),
    freshness: {
      tier: "fresh",
      label: "Fresh",
      updated_at: new Date(Date.now() - 10 * 60_000).toISOString(),
      detail: "Updated recently",
    },
  },
  {
    id: "alt-1",
    label: "alternative",
    title: "Alternative",
    via: "via Vikram Marg",
    distance_m: 12800,
    duration_s: 32 * 60,
    safety: {
      value: 62,
      band: "moderate",
      confidence: "medium",
      evidence: {
        sources: [],
        confidence: "medium",
        confidence_value: 0.5,
        freshness: {
          tier: "aging",
          label: "Aging",
          updated_at: new Date(Date.now() - 2 * 86_400_000).toISOString(),
          detail: "Updated 2 days ago",
        },
        conflicts: [{ observation_type: "poor_lighting", detail: "Conflicting reports detected" }],
        coverage: 0.6,
      },
    },
    indicators: ["Moderate Lighting", "Some Crowd"],
    route_type: "balanced",
    geometry: {
      type: "LineString",
      coordinates: buildGeometry(
        INDIA_GATE,
        AKSHARDHAM,
        [
          [28.632, 77.245],
          [28.625, 77.265],
        ],
        2,
      ),
    },
    risk_colors: riskColorsFor(SAFETY_MID),
    freshness: {
      tier: "aging",
      label: "Aging",
      updated_at: new Date(Date.now() - 2 * 86_400_000).toISOString(),
      detail: "Updated 2 days ago",
    },
  },
  {
    id: "short-1",
    label: "shortest",
    title: "Shortest",
    via: "via Ring Road",
    distance_m: 9600,
    duration_s: 24 * 60,
    safety: {
      value: 45,
      band: "moderate",
      confidence: "low",
      evidence: {
        sources: [],
        confidence: "low",
        confidence_value: 0.32,
        freshness: {
          tier: "stale",
          label: "Stale",
          updated_at: new Date(Date.now() - 120 * 86_400_000).toISOString(),
          detail: "Updated 4 months ago",
        },
        conflicts: [
          { observation_type: "harassment", detail: "Conflicting reports detected" },
          { observation_type: "streetlight_not_working", detail: "Lighting status uncertain" },
        ],
        coverage: 0.35,
      },
    },
    indicators: ["Unlit Stretch", "Heavy Crowd"],
    route_type: "time_priority",
    geometry: {
      type: "LineString",
      coordinates: buildGeometry(
        INDIA_GATE,
        AKSHARDHAM,
        [
          [28.606, 77.244],
          [28.6, 77.26],
        ],
        3,
      ),
    },
    risk_colors: riskColorsFor(SAFETY_SHORT),
    freshness: {
      tier: "stale",
      label: "Stale",
      updated_at: new Date(Date.now() - 120 * 86_400_000).toISOString(),
      detail: "Updated 4 months ago",
    },
  },
];

export const MOCK_INCIDENTS: Incident[] = [
  {
    id: "inc-1",
    category: "harassment",
    severity: "high",
    location: { name: "Connaught Place", lat: 28.6314, lon: 77.2167 },
    reported_at: new Date(Date.now() - 2 * 60_000).toISOString(),
    summary: "Harassment reported near central plaza",
    verified: true,
    source: "Community report",
  },
  {
    id: "inc-2",
    category: "poor_lighting",
    severity: "moderate",
    location: { name: "ITO Area", lat: 28.6289, lon: 77.2409 },
    reported_at: new Date(Date.now() - 5 * 60_000).toISOString(),
    summary: "Poor lighting on service lane",
    verified: false,
    source: "Community report",
  },
  {
    id: "inc-3",
    category: "road_work",
    severity: "low",
    location: { name: "Ring Road", lat: 28.6109, lon: 77.2428 },
    reported_at: new Date(Date.now() - 15 * 60_000).toISOString(),
    summary: "Road work narrowing footpath",
    verified: false,
    source: "OpenStreetMap",
  },
  {
    id: "inc-4",
    category: "crowd_alert",
    severity: "moderate",
    location: { name: "Lajpat Nagar", lat: 28.5684, lon: 77.2546 },
    reported_at: new Date(Date.now() - 20 * 60_000).toISOString(),
    summary: "Dense crowd near market entrance",
    verified: false,
    source: "Community report",
  },
  {
    id: "inc-5",
    category: "streetlight_not_working",
    severity: "moderate",
    location: { name: "India Gate", lat: 28.6105, lon: 77.2317 },
    reported_at: new Date(Date.now() - 45 * 60_000).toISOString(),
    summary: "Broken streetlight, 2 reports",
    verified: true,
    source: "Verified report",
  },
  {
    id: "inc-6",
    category: "suspicious_activity",
    severity: "high",
    location: { name: "Karol Bagh", lat: 28.6519, lon: 77.1908 },
    reported_at: new Date(Date.now() - 70 * 60_000).toISOString(),
    summary: "Suspicious activity reported",
    verified: false,
    source: "Community report",
  },
];

export const MOCK_LIGHTING: (LightingObservation & { lat: number; lon: number })[] = [
  {
    working: true,
    status_label: "Lighting evidence available",
    confidence: "high",
    source: "City data",
    observed_at: new Date(Date.now() - 3 * 3600_000).toISOString(),
    lat: 28.625,
    lon: 77.24,
  },
  {
    working: null,
    status_label: "Lighting status uncertain",
    confidence: "low",
    source: "Community reports conflict",
    observed_at: new Date(Date.now() - 48 * 3600_000).toISOString(),
    lat: 28.618,
    lon: 77.255,
  },
  {
    working: false,
    status_label: "Lighting evidence available (not working)",
    confidence: "medium",
    source: "Community report",
    observed_at: new Date(Date.now() - 5 * 3600_000).toISOString(),
    lat: 28.6105,
    lon: 77.2317,
  },
  {
    working: true,
    status_label: "Lighting evidence available",
    confidence: "medium",
    source: "OpenStreetMap",
    observed_at: new Date(Date.now() - 7 * 86_400_000).toISOString(),
    lat: 28.632,
    lon: 77.245,
  },
];

export const MOCK_FACILITIES: Facility[] = [
  {
    id: "f1",
    type: "police",
    name: "Connaught Place Police Station",
    lat: 28.6325,
    lon: 77.2176,
    distance_m: 640,
  },
  {
    id: "f2",
    type: "hospital",
    name: "Ram Manohar Lohia Hospital",
    lat: 28.6267,
    lon: 77.2193,
    distance_m: 980,
  },
  {
    id: "f3",
    type: "fire_station",
    name: "Fire Station, Paharganj",
    lat: 28.6451,
    lon: 77.2126,
    distance_m: 2200,
  },
  {
    id: "f4",
    type: "pharmacy",
    name: "Apollo Pharmacy, India Gate",
    lat: 28.6118,
    lon: 77.2321,
    distance_m: 210,
  },
  {
    id: "f5",
    type: "transit_stop",
    name: "Rajiv Chowk Metro",
    lat: 28.6328,
    lon: 77.2197,
    distance_m: 400,
  },
  {
    id: "f6",
    type: "hospital",
    name: "Safdarjung Hospital",
    lat: 28.5831,
    lon: 77.2114,
    distance_m: 4200,
  },
];

export const MOCK_ALERTS: Incident[] = [
  MOCK_INCIDENTS[0],
  MOCK_INCIDENTS[1],
  MOCK_INCIDENTS[2],
  MOCK_INCIDENTS[3],
];

export const MOCK_COMMUNITY: CommunityPost[] = [
  {
    id: "p1",
    kind: "alert",
    text: "Shared an alert: harassment near Connaught Place inner circle.",
    location: "Connaught Place",
    status: "VERIFIED",
    created_at: new Date(Date.now() - 12 * 60_000).toISOString(),
  },
  {
    id: "p2",
    kind: "route_update",
    text: "Route update: Tilak Marg footpath reopened after road work.",
    location: "Tilak Marg",
    status: "VERIFIED",
    created_at: new Date(Date.now() - 60 * 60_000).toISOString(),
  },
  {
    id: "p3",
    kind: "photo",
    text: "Photo shared: new streetlight installed near ITO crossing.",
    location: "ITO Area",
    status: "VERIFIED",
    created_at: new Date(Date.now() - 3 * 3600_000).toISOString(),
  },
];

export const MOCK_AREA_SAFETY: AreaSafety = {
  area_name: "Connaught Place",
  score: {
    value: 68,
    band: "moderate",
    confidence: "medium",
    evidence: {
      sources: [],
      confidence: "medium",
      confidence_value: 0.55,
      freshness: {
        tier: "fresh",
        label: "Fresh",
        updated_at: new Date(Date.now() - 25 * 60_000).toISOString(),
        detail: "Updated recently",
      },
      conflicts: [{ observation_type: "poor_lighting", detail: "Conflicting reports detected" }],
      coverage: 0.66,
    },
  },
  recent_incidents: 3,
  lighting_summary: "Moderate evidence",
  crowd: "medium",
  by_time_of_day: [
    { hour: 0, score: 41, confidence: 0.3 },
    { hour: 4, score: 38, confidence: 0.25 },
    { hour: 8, score: 72, confidence: 0.6 },
    { hour: 12, score: 81, confidence: 0.7 },
    { hour: 16, score: 78, confidence: 0.65 },
    { hour: 20, score: 55, confidence: 0.45 },
  ],
};

export const MOCK_INSIGHTS = {
  overall: {
    value: 68,
    band: "moderate" as const,
    confidence_value: 0.55,
    coverage: 0.66,
  },
  recent_incidents: 14,
  lighting_working_share: 0.72,
  lighting_uncertain_share: 0.18,
  crowd_level: "medium" as const,
  facilities_nearby: 6,
  road_conditions: { good: 0.61, fair: 0.27, poor: 0.12 },
  freshness: { fresh: 0.58, aging: 0.27, stale: 0.15 },
  conflicting: 2,
  by_time_of_day: MOCK_AREA_SAFETY.by_time_of_day,
  by_segment: [
    { segment: "Tilak Marg", score: 82, confidence: 0.7 },
    { segment: "Vikram Marg", score: 61, confidence: 0.5 },
    { segment: "Ring Road", score: 44, confidence: 0.3 },
    { segment: "ITO Crossing", score: 58, confidence: 0.45 },
    { segment: "Akshardham Lane", score: 71, confidence: 0.55 },
  ],
};

export const MOCK_HEATMAP = {
  label: "Based on available reports and evidence",
  zones: [
    { name: "Connaught Place", lat: 28.6314, lon: 77.2167, level: 0.35 },
    { name: "Rajiv Chowk", lat: 28.6328, lon: 77.2197, level: 0.5 },
    { name: "India Gate", lat: 28.6129, lon: 77.2295, level: 0.55 },
    { name: "ITO", lat: 28.6289, lon: 77.2409, level: 0.4 },
    { name: "Lajpat Nagar", lat: 28.5684, lon: 77.2546, level: 0.28 },
    { name: "Karol Bagh", lat: 28.6519, lon: 77.1908, level: 0.22 },
  ],
};

export const MOCK_GEOCODE: GeocodeResult[] = [
  { name: "Connaught Place", kind: "area", type: null, lat: 28.6314, lon: 77.2167 },
  { name: "Rajiv Chowk", kind: "area", type: null, lat: 28.6328, lon: 77.2197 },
  { name: "India Gate", kind: "area", type: null, lat: 28.6129, lon: 77.2295 },
  {
    name: "Connaught Police Station",
    kind: "facility",
    type: "police",
    lat: 28.6305,
    lon: 77.2148,
  },
  {
    name: "Karol Bagh Police Station",
    kind: "facility",
    type: "police",
    lat: 28.6519,
    lon: 77.1908,
  },
];

export const MOCK_ADMIN_REPORTS: AdminReport[] = [
  {
    report_id: 7401,
    segment_id: 456736,
    category: "harassment",
    verification_state: "pending",
    reported_at: new Date(Date.now() - 86400000).toISOString(),
    confidence: 0.62,
  },
  {
    report_id: 7402,
    segment_id: 457230,
    category: "poor_lighting",
    verification_state: "CORROBORATED",
    reported_at: new Date(Date.now() - 172800000).toISOString(),
    confidence: 0.71,
  },
];

export function mockScoreForSegment(risk: number): ReturnType<typeof scoreFromRisk> {
  return scoreFromRisk(risk, Math.max(0.25, 1 - risk * 4));
}
