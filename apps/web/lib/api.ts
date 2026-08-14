import { adaptRouteResult } from "./adapt";
import {
  MOCK_ALERTS,
  MOCK_AREA_SAFETY,
  MOCK_COMMUNITY,
  MOCK_FACILITIES,
  MOCK_HEATMAP,
  MOCK_INCIDENTS,
  MOCK_LIGHTING,
  MOCK_ROUTE_CANDIDATES,
} from "./mock-data";
import { scoreFromRisk } from "./score";
import type {
  AreaSafety,
  CommunityPost,
  Facility,
  HeatZone,
  Incident,
  LightingObservation,
  ReportResult,
  ReportSubmission,
  RouteCandidate,
  RouteRequest,
  RoutesResponse,
  SafetyEvidence,
  SafetySegment,
} from "./types";

/**
 * API layer. Components never call fetch directly.
 *
 * REAL API is the default (source of truth). Set NEXT_PUBLIC_USE_MOCK=true
 * only for local UI work without the backend; mock data is typed but the
 * production demo must never ship it.
 */

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number | null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const DEFAULT_API_URL = "http://localhost:8000";

export function apiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL;
}

async function parseError(resp: Response): Promise<ApiError> {
  let detail: string | null = null;
  try {
    const body = await resp.json();
    if (typeof body?.detail === "string") {
      detail = body.detail;
    }
  } catch {
    // non-JSON error body
  }
  const message = detail ?? `Request failed (HTTP ${resp.status})`;
  return new ApiError(message, resp.status);
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(`${apiUrl()}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      `Cannot reach the API at ${apiUrl()}. Start the backend and try again.`,
      null,
    );
  }
  if (!resp.ok) {
    throw await parseError(resp);
  }
  return (await resp.json()) as T;
}

async function getJson<T>(path: string): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(`${apiUrl()}${path}`);
  } catch {
    throw new ApiError(`Cannot reach the API at ${apiUrl()}.`, null);
  }
  if (!resp.ok) {
    throw await parseError(resp);
  }
  return (await resp.json()) as T;
}

/* ---------------- Routes ---------------- */

export async function requestRoutes(req: RouteRequest): Promise<RouteCandidate[]> {
  if (USE_MOCK) {
    // Simulate the real pipeline's latency so UI states are exercised.
    await new Promise((r) => setTimeout(r, 900));
    return MOCK_ROUTE_CANDIDATES;
  }
  const resp = await postJson<RoutesResponse>("/api/routes", req);
  return resp.routes.map((route, i) => adaptRouteResult(route, i));
}

/* ---------------- Evidence ---------------- */

/** Raw response of GET /api/segments/{segment_id}/evidence. */
interface SegmentEvidenceResponse {
  segment_id: number;
  sources: { name: string; reliability: number }[];
  confidence: number;
  freshness: { updated_at: string | null; age_hours: number | null };
  conflicts: { observation_type: string; detail: string }[];
  coverage: number;
}

function freshnessTier(ageHours: number | null): "fresh" | "aging" | "stale" | "unknown" {
  if (ageHours === null) return "unknown";
  if (ageHours <= 24) return "fresh";
  if (ageHours <= 72) return "aging";
  return "stale";
}

export async function fetchSegmentEvidence(segmentId: number): Promise<SafetyEvidence> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 250));
    return {
      sources: [
        {
          id: "s1",
          name: "Community Reports",
          kind: "community",
          reliability: 0.6,
          freshness: {
            tier: "fresh",
            label: "Fresh",
            updated_at: new Date().toISOString(),
            detail: "Updated recently",
          },
        },
        {
          id: "s2",
          name: "OpenStreetMap",
          kind: "osm",
          reliability: 0.7,
          freshness: {
            tier: "aging",
            label: "Aging",
            updated_at: new Date(Date.now() - 2 * 86400000).toISOString(),
            detail: "Updated 2 days ago",
          },
        },
        {
          id: "s3",
          name: "Public Data",
          kind: "public",
          reliability: 0.9,
          freshness: {
            tier: "fresh",
            label: "Fresh",
            updated_at: new Date(Date.now() - 86400000).toISOString(),
            detail: "Updated recently",
          },
        },
      ],
      confidence: "medium",
      confidence_value: 0.55,
      freshness: {
        tier: "fresh",
        label: "Fresh",
        updated_at: new Date().toISOString(),
        detail: "Updated recently",
      },
      conflicts: [{ observation_type: "poor_lighting", detail: "Conflicting reports detected" }],
      coverage: 0.66,
    };
  }
  const raw = await getJson<SegmentEvidenceResponse>(`/api/segments/${segmentId}/evidence`);
  const tier = freshnessTier(raw.freshness.age_hours);
  return {
    sources: raw.sources.map((s, i) => ({
      id: `src-${segmentId}-${i}`,
      name: s.name,
      kind: "osm" as const,
      reliability: s.reliability,
      freshness: {
        tier,
        label:
          tier === "unknown"
            ? "Unknown"
            : tier === "fresh"
              ? "Fresh"
              : tier === "aging"
                ? "Aging"
                : "Stale",
        updated_at: raw.freshness.updated_at,
        detail:
          raw.freshness.age_hours === null
            ? "Evidence age not exposed by the API"
            : `Updated ${Math.round(raw.freshness.age_hours)}h ago`,
      },
    })),
    confidence: tier === "unknown" ? "low" : "medium",
    confidence_value: raw.confidence,
    freshness: {
      tier,
      label:
        tier === "unknown"
          ? "Unknown"
          : tier === "fresh"
            ? "Fresh"
            : tier === "aging"
              ? "Aging"
              : "Stale",
      updated_at: raw.freshness.updated_at,
      detail:
        raw.freshness.age_hours === null
          ? "Evidence age not exposed by the API"
          : `Updated ${Math.round(raw.freshness.age_hours)}h ago`,
    },
    conflicts: raw.conflicts.map((c) => ({
      observation_type: c.observation_type,
      detail: c.detail,
    })),
    coverage: raw.coverage,
  };
}

export async function fetchSegmentsByArea(lat: number, lon: number): Promise<SafetySegment[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200));
    return [0.03, 0.07, 0.14, 0.05, 0.1].map((risk, i) => ({
      segment_id: 456700 + i,
      risk_probability: risk,
      safety_score: scoreFromRisk(risk, 0.6),
      lighting: MOCK_LIGHTING[i % MOCK_LIGHTING.length] ?? null,
      crowd: (["low", "medium", "high"] as const)[i % 3],
      recent_incidents: i % 3,
      road_type: ["residential", "primary", "footway", "secondary", "service"][i],
      freshness: {
        tier: "fresh",
        label: "Fresh",
        updated_at: new Date().toISOString(),
        detail: "Updated recently",
      },
    }));
  }
  return getJson<SafetySegment[]>(`/api/evidence/segments?lat=${lat}&lon=${lon}`);
}

/* ---------------- Overlay data ---------------- */

export async function fetchIncidents(): Promise<Incident[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300));
    return MOCK_INCIDENTS;
  }
  return getJson<Incident[]>("/api/incidents");
}

export async function fetchAlerts(): Promise<Incident[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200));
    return MOCK_ALERTS;
  }
  return getJson<Incident[]>("/api/alerts");
}

/** Map markers need coordinates; the (future) lighting endpoint is expected to provide them. */
export async function fetchLighting(): Promise<
  (LightingObservation & { lat: number; lon: number })[]
> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 250));
    return MOCK_LIGHTING;
  }
  return getJson<(LightingObservation & { lat: number; lon: number })[]>("/api/lighting");
}
export async function fetchFacilities(): Promise<Facility[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200));
    return MOCK_FACILITIES;
  }
  return getJson<Facility[]>("/api/facilities");
}

export async function fetchCommunity(): Promise<CommunityPost[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200));
    return MOCK_COMMUNITY;
  }
  return getJson<CommunityPost[]>("/api/community");
}

export async function fetchAreaSafety(): Promise<AreaSafety> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300));
    return MOCK_AREA_SAFETY;
  }
  return getJson<AreaSafety>("/api/safety/area?name=connaught-place");
}

export async function fetchHeatmapZones() {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300));
    return MOCK_HEATMAP;
  }
  const zones = await getJson<HeatZone[]>("/api/safety/heatmap");
  return { zones };
}

/* ---------------- Reports ---------------- */

export async function submitReport(submission: ReportSubmission): Promise<ReportResult> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 800));
    return {
      report_id: 7401 + Math.floor(Math.random() * 100),
      segment_id: submission.segment_id,
      category: submission.category,
      verification_state: "pending",
      model_version: "mock-v0",
    };
  }
  return postJson<ReportResult>("/api/reports", submission);
}
