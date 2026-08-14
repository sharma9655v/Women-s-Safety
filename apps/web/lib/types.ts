/** Typed API contracts for Map for Women.
 *
 * The UI never invents safety data: every component consumes these types,
 * so real FastAPI responses can replace mock data without redesign.
 */

export interface LatLon {
  lat: number;
  lon: number;
}

export type RouteMode = "walking" | "driving" | "cycling";

export type SafetyPreference = "safety" | "balanced" | "time";

export interface RouteRequest {
  origin: LatLon;
  destination: LatLon;
  mode: RouteMode;
  safety_preference: SafetyPreference;
  /** Optional simulated IST hour (0-23) for demo; the UI labels it as such. */
  hour_ist?: number;
}

export interface RouteGeometry {
  type: "LineString";
  coordinates: [number, number][];
}

export type RouteType = "safety_priority" | "balanced" | "time_priority";

/** API contract (apps/api `RouteResult`). */
export interface RouteResult {
  route_type: RouteType;
  distance_m: number;
  duration_s: number;
  risk_probability: number;
  estimated_safety: number;
  confidence: number;
  uncertainty: number;
  warnings: string[];
  reasons: string[];
  model_version: string;
  segment_ids: number[];
  geometry: RouteGeometry;
}

export interface RoutesResponse {
  routes: RouteResult[];
}

/* ------------------------------------------------------------------ */
/* Evidence / safety domain (section 33: real-data-ready interfaces)   */
/* ------------------------------------------------------------------ */

export type ConfidenceLevel = "high" | "medium" | "low";

export type FreshnessTier = "fresh" | "aging" | "stale" | "unknown";

export type SafetyBand = "high" | "moderate" | "low" | "limited";

export interface DataFreshness {
  tier: FreshnessTier;
  label: string;
  updated_at: string | null;
  detail: string;
}

export interface EvidenceSource {
  id: string;
  name: string;
  kind: "community" | "osm" | "public" | "verified" | "report";
  reliability: number;
  freshness: DataFreshness;
}

export interface EvidenceConflict {
  observation_type: string;
  detail: string;
}

export interface SafetyEvidence {
  sources: EvidenceSource[];
  confidence: ConfidenceLevel;
  confidence_value: number; // 0..1
  freshness: DataFreshness;
  conflicts: EvidenceConflict[];
  /** 0..1 share of known evidence, or null when the API does not report it. */
  coverage: number | null;
}

export interface SafetyScore {
  value: number; // 0..100 — an ESTIMATE from available evidence, never absolute
  band: SafetyBand;
  confidence: ConfidenceLevel;
  evidence: SafetyEvidence;
}

export interface SafetySegment {
  segment_id: number;
  risk_probability: number;
  safety_score: SafetyScore;
  lighting: LightingObservation | null;
  crowd: CrowdLevel | null;
  recent_incidents: number;
  road_type: string;
  freshness: DataFreshness;
}

export type CrowdLevel = "low" | "medium" | "high";

export type IncidentCategory =
  | "harassment"
  | "poor_lighting"
  | "road_work"
  | "crowd_alert"
  | "suspicious_activity"
  | "road_hazard"
  | "streetlight_not_working"
  | "other";

export type IncidentSeverity = "low" | "moderate" | "high" | "critical";

export interface Incident {
  id: string;
  category: IncidentCategory;
  severity: IncidentSeverity;
  location: { name: string; lat: number; lon: number };
  reported_at: string; // ISO
  summary: string;
  verified: boolean;
  source: string;
}

export interface LightingObservation {
  working: boolean | null; // null = uncertain — never claim "streetlight is working"
  status_label: string; // "Lighting evidence available" | "Lighting status uncertain" ...
  confidence: ConfidenceLevel;
  source: string;
  observed_at: string | null;
}

export interface Facility {
  id: string;
  type: "police" | "hospital" | "pharmacy" | "fire_station" | "transit_stop" | "public_place";
  name: string;
  lat: number;
  lon: number;
  distance_m: number | null;
}

export interface AreaSafety {
  area_name: string;
  score: SafetyScore;
  recent_incidents: number;
  lighting_summary: string;
  crowd: CrowdLevel;
  by_time_of_day: { hour: number; score: number; confidence: number }[];
}

export interface HeatZone {
  name: string;
  lat: number;
  lon: number;
  level: number;
}

export interface HeatmapResponse {
  zones: HeatZone[];
}

/* ------------------------------------------------------------------ */
/* Route candidates & community                                       */
/* ------------------------------------------------------------------ */

export interface RouteCandidate {
  id: string;
  label: "recommended" | "alternative" | "shortest";
  title: string;
  via: string;
  distance_m: number;
  duration_s: number;
  safety: SafetyScore;
  indicators: string[];
  route_type: RouteType;
  geometry: RouteGeometry;
  /** Per-coordinate risk coloring (synthesized from segment evidence). */
  risk_colors: string[];
  freshness: DataFreshness;
  /** Real-API extras (absent in mock data). */
  uncertainty?: number;
  reasons?: string[];
  warnings?: string[];
  model_version?: string;
  segment_ids?: number[];
}

export interface CommunityPost {
  id: string;
  author: string;
  author_initials: string;
  kind: "alert" | "route_update" | "photo";
  text: string;
  location: string;
  time_ago: string;
  likes: number;
  comments: number;
  verified: boolean;
}

export interface ReportCategoryOption {
  id: string;
  label: string;
}

export interface ReportSubmission {
  /** Road segment the report is about (required by the API). */
  segment_id: number;
  category: string;
  description: string | null;
  evidence_image: string | null;
}

export interface ReportResult {
  report_id: number;
  segment_id: number;
  category: string;
  verification_state: string;
  model_version: string;
}
