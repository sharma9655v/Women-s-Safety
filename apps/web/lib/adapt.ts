import { bandForScore, confidenceLevel, riskColor } from "./score";
import type { RouteCandidate, RouteResult, RouteType } from "./types";

/**
 * Adapter from the real FastAPI RouteResult to the UI's RouteCandidate.
 *
 * The API is the source of truth: everything here is derived from real
 * response fields (risk_probability, confidence, uncertainty, warnings,
 * reasons, model_version). No safety data is invented. Fields the API does
 * not expose (per-segment evidence, freshness) are left unknown/empty so the
 * UI shows "Limited Safety Data" instead of fabricated numbers.
 */

const TITLES: Record<RouteType, string> = {
  safety_priority: "Safety Priority",
  balanced: "Balanced",
  time_priority: "Time Priority",
};

export function adaptRouteResult(route: RouteResult, index: number): RouteCandidate {
  const risk = Math.max(0, Math.min(1, route.risk_probability));
  const confidence = confidenceLevel(route.confidence);
  // API geometry is [lon, lat] (OSRM order); the UI renders [lat, lon].
  const coordinates = route.geometry.coordinates.map(
    ([lon, lat]) => [lat, lon] as [number, number],
  );
  const color = riskColor(risk);
  const freshness = {
    tier: "unknown" as const,
    label: "Unknown",
    updated_at: null as string | null,
    detail: "Evidence age not exposed by the API",
  };

  return {
    id: `route-${route.route_type}`,
    label: index === 0 ? "recommended" : index === 1 ? "alternative" : "shortest",
    title: TITLES[route.route_type],
    via: (route.reasons[0] ?? "").slice(0, 60),
    distance_m: route.distance_m,
    duration_s: route.duration_s,
    safety: {
      value: route.estimated_safety,
      band: bandForScore(route.estimated_safety),
      confidence,
      evidence: {
        sources: [],
        confidence,
        confidence_value: route.confidence,
        freshness,
        conflicts: [],
        coverage: null,
      },
    },
    indicators: route.warnings.slice(0, 3),
    route_type: route.route_type,
    geometry: { type: "LineString", coordinates },
    risk_colors: Array.from({ length: Math.max(1, coordinates.length - 1) }, () => color),
    freshness,
    uncertainty: route.uncertainty,
    reasons: route.reasons,
    warnings: route.warnings,
    model_version: route.model_version,
    segment_ids: route.segment_ids,
  };
}
