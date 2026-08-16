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
  /** Length-weighted share of the route at risk >= 0.5 (0-1). */
  high_risk_fraction?: number;
  /** Effective risky metres: sum(length x risk) over matched segments. */
  risk_exposure_m?: number;
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
  /** Always null today: no crowd data source exists. */
  crowd: CrowdLevel | null;
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
  /** Length-weighted share of the route at risk >= 0.5 (0-1). */
  high_risk_fraction?: number;
  /** Effective risky metres: sum(length x risk) over matched segments. */
  risk_exposure_m?: number;
  /** Backend-derived probability of risk along the route (0-1). */
  risk_probability?: number;
  /** Backend-derived model confidence (0-1). */
  confidence_value?: number;
}

/** One result of the /api/geocode search (areas and facilities). */
export interface GeocodeResult {
  name: string;
  kind: "area" | "facility";
  type: string | null;
  lat: number;
  lon: number;
}

/** Admin review row from /api/admin/reports (privacy-filtered). */
export interface AdminReport {
  report_id: number;
  segment_id: number;
  category: string;
  verification_state: string;
  reported_at: string;
  confidence: number;
}

/** One item of the public community feed (GET /api/community contract).
 * Authorship is anonymous by design — the API never exposes a poster identity. */
export interface CommunityPost {
  id: string;
  kind: "alert" | "route_update" | "photo";
  location: string;
  text: string;
  /** "VERIFIED" | "PENDING" | "REJECTED" — the public feed only shows VERIFIED. */
  status: string;
  created_at: string;
}

export interface CommunityPostInput {
  kind: "alert" | "route_update" | "photo";
  location: string;
  text: string;
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

/* ------------------------------------------------------------------ */
/* Evidence engine (lifecycle demo)                                    */
/* ------------------------------------------------------------------ */

export interface EvidenceTypeSummary {
  observation_type: string;
  count: number;
  score: number;
  freshness: number;
  confidence: number;
  conflicts: boolean;
  source_counts: Record<string, number>;
  state_counts: Record<string, number>;
  distinct_source_types: number;
  corroborated: boolean;
}

export interface SegmentEvidence {
  segment_id: number;
  total_observations: number;
  overall_freshness: number;
  overall_confidence: number;
  conflicts: string[];
  by_type: Record<string, EvidenceTypeSummary>;
  model_version: string;
}

/* ------------------------------------------------------------------ */
/* Personal safety (Phase 9): contacts / emergency / sharing           */
/* ------------------------------------------------------------------ */

export type ContactRole = "primary" | "secondary";

export interface TrustedContact {
  id: number;
  name: string;
  relationship: string;
  phone: string;
  role: ContactRole;
  enabled: boolean;
}

export interface ContactInput {
  name: string;
  relationship: string;
  phone: string;
  role: ContactRole;
}

export interface ContactUpdate {
  name?: string;
  relationship?: string;
  phone?: string;
  role?: ContactRole;
  enabled?: boolean;
}

export type EmergencyStatus = "ACTIVE" | "ENDED";

export interface EmergencySession {
  session_id: string;
  status: EmergencyStatus;
  started_at: string;
  ended_at: string | null;
  end_reason: string | null;
  latitude: number | null;
  longitude: number | null;
  last_known_at: string | null;
  notified_contact_ids: number[];
  /** Honest delivery state: "no_channel" | "queued" | "sent" | "failed". */
  notify_status: string;
  location_sharing: string | null;
}

export type SharingKind = "EMERGENCY" | "GUARDIAN";
export type SharingStatus = "ACTIVE" | "STOPPED" | "EXPIRED";

export interface SharingSession {
  session_id: string;
  kind: SharingKind;
  status: SharingStatus;
  started_at: string;
  expires_at: string;
  stopped_at: string | null;
  latitude: number | null;
  longitude: number | null;
  last_updated_at: string | null;
  recipient_ids: number[];
}

export interface NotificationEvent {
  id: number;
  type: string;
  channel: string;
  /** Honest status: "no_channel" | "queued" | "sent" | "failed". */
  status: string;
  payload: Record<string, unknown>;
  created_at: string;
}

/* ------------------------------------------------------------------ */
/* Privacy center (Feature Group X): per-device settings               */
/* ------------------------------------------------------------------ */

export interface PrivacySettings {
  voice_guidance_enabled: boolean;
  voice_language: string;
  discreet_mode_enabled: boolean;
}

/** GET /api/privacy/dashboard — the backend's own privacy summary.
 * Report history is anonymous and is NOT listed here (by design). */
export interface PrivacyDashboard {
  location_sharing_active: boolean;
  location_sharing_expires_at: string | null;
  guardian_active: boolean;
  guardian_checkin_deadline: string | null;
  trusted_contact_count: number;
  emergency_active: boolean;
  emergency_notify_status: string | null;
  voice_guidance_active: boolean;
  voice_language: string;
  discreet_mode_enabled: boolean;
}

/* ------------------------------------------------------------------ */
/* Guardian journeys (Phase 10): check-ins and staged escalation        */
/* ------------------------------------------------------------------ */

export type GuardianStatus = "ACTIVE" | "COMPLETED" | "CANCELLED" | "ESCALATED";

export interface GuardianSession {
  session_id: string;
  status: GuardianStatus;
  started_at: string;
  ended_at: string | null;
  end_reason: string | null;
  guardian_contact_ids: number[];
  expected_arrival_at: string | null;
  /** When a check-in is due; escalations start after this passes. */
  checkin_deadline: string;
  checkin_grace_s: number;
  last_checkin_at: string | null;
  latitude: number | null;
  longitude: number | null;
  last_known_at: string | null;
  deviation_detected: boolean;
  first_deviation_at: string | null;
  /** 0 = ok, 1 = check-in missed, 2 = escalated to contacts. */
  escalation_stage: number;
}

export interface GuardianCreateInput {
  guardian_contact_ids: number[];
  expected_arrival_at?: string | null;
  /** Planned route as [lon, lat] pairs — used only for deviation checks. */
  planned_geometry?: [number, number][] | null;
  checkin_grace_s?: number;
}

export interface GuardianEndResult {
  session_id: string;
  status: GuardianStatus;
  ended_at: string;
  end_reason: string;
}

/* ------------------------------------------------------------------ */
/* Safety preferences (Feature Group Q): GET/PUT /api/preferences      */
/* ------------------------------------------------------------------ */

export interface SafetyPreferences {
  client_id: string;
  prefer_better_lit: boolean;
  prefer_main_roads: boolean;
  prefer_near_emergency: boolean;
  avoid_known_hazards: boolean;
  avoid_isolated_roads: boolean;
  minimize_walking_time: boolean;
  /** "balanced" | "safety" | "time" — maps to the routing safety_preference. */
  default_profile: SafetyPreference;
  discreet_mode_enabled: boolean;
  voice_guidance_enabled: boolean;
  voice_language: string;
}

/* ------------------------------------------------------------------ */
/* Discreet mode (Feature Group R): GET/PUT /api/discreet-mode         */
/* ------------------------------------------------------------------ */

export interface DiscreetModeSettings {
  client_id: string;
  enabled: boolean;
  quick_sos_gesture: string;
  exit_to_neutral_app: boolean;
  neutral_app_label: string;
  neutral_app_icon: string;
}

/* ------------------------------------------------------------------ */
/* Fake call (Feature Group T): POST/GET /api/fake-call                */
/* ------------------------------------------------------------------ */

export interface FakeCallSession {
  id: string;
  caller_name: string;
  caller_number: string | null;
  scheduled_at: string;
  /** "SCHEDULED" | "TRIGGERED" | "DISMISSED" | "EXPIRED". */
  status: string;
}

export interface FakeCallInput {
  caller_name: string;
  caller_number?: string | null;
  /** Optional ISO timestamp; the backend defaults to now when omitted. */
  scheduled_at?: string | null;
}

/* ------------------------------------------------------------------ */
/* Voice guidance (Feature Group U): /api/voice/start|stop|status      */
/* ------------------------------------------------------------------ */

export interface VoiceGuidanceStatus {
  session_id: string;
  client_id: string;
  route_session_id: string | null;
  language: string;
  active: boolean;
  started_at: string;
  ended_at: string | null;
}

/* ------------------------------------------------------------------ */
/* Journey check-ins (Feature Group V): /api/journey/checkins          */
/* ------------------------------------------------------------------ */

export type JourneyStatus = "ACTIVE" | "COMPLETED" | "CANCELLED" | "ESCALATED" | "MISSED";

export interface JourneyCheckinSession {
  session_id: string;
  status: JourneyStatus;
  started_at: string;
  ended_at: string | null;
  end_reason: string | null;
  destination_name: string;
  destination_lat: number | null;
  destination_lon: number | null;
  expected_arrival_at: string | null;
  checkin_interval_s: number;
  checkin_grace_s: number;
  last_checkin_at: string | null;
  next_checkin_at: string | null;
  contact_ids: number[];
  escalation_stage: number;
  notified_stage: number;
  latitude: number | null;
  longitude: number | null;
  last_known_at: string | null;
}

export interface JourneyCheckinInput {
  destination_name: string;
  destination_lat: number | null;
  destination_lon: number | null;
  expected_arrival_at?: string | null;
  checkin_interval_s?: number;
  checkin_grace_s?: number;
  contact_ids: number[];
}

export interface JourneyEndResult {
  session_id: string;
  status: JourneyStatus;
  ended_at: string;
  end_reason: string;
}

/* ------------------------------------------------------------------ */
/* Model traceability: GET /api/models/current                         */
/* ------------------------------------------------------------------ */

export interface MlGate {
  open: boolean;
  verified_observations: number;
  span_days: number | null;
  min_verified_observations: number;
  min_span_days: number;
}

export interface ModelsCurrent {
  risk_model: string;
  evidence_model: string;
  dataset_versions: string[];
  ml_gate: MlGate;
}
