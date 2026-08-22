/** Typed API contracts for Map for Women — generated from live OpenAPI + manual curation.
 *  The UI never invents safety data; every component consumes these types.
 */

export interface LatLon { lat: number; lon: number; }

export type RouteMode = "walking" | "driving" | "cycling";
export type SafetyPreference = "safety" | "balanced" | "time";

export interface RouteRequest {
  origin: LatLon;
  destination: LatLon;
  mode: RouteMode;
  safety_preference: SafetyPreference;
  hour_ist?: number;
}

export interface RouteGeometry {
  type: "LineString";
  coordinates: [number, number][];
}

export type RouteType = "safety_priority" | "balanced" | "time_priority";

export interface RouteResult {
  route_type: RouteType;
  distance_m: number;
  duration_s: number;
  risk_probability: number;
  estimated_safety: number;
  confidence: number;
  uncertainty: number;
  high_risk_fraction?: number;
  risk_exposure_m?: number;
  warnings: string[];
  reasons: string[];
  model_version: string;
  segment_ids: number[];
  geometry: RouteGeometry;
}

export interface RoutesResponse { routes: RouteResult[]; }

/* ------------------------------------------------------------------ */
/* Evidence / safety domain                                            */
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
  confidence_value: number;
  freshness: DataFreshness;
  conflicts: EvidenceConflict[];
  coverage: number | null;
}

export interface SafetyScore {
  value: number;
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
  | "harassment" | "poor_lighting" | "road_work" | "crowd_alert"
  | "suspicious_activity" | "road_hazard" | "streetlight_not_working" | "other";

export type IncidentSeverity = "low" | "moderate" | "high" | "critical";

export interface Incident {
  id: string;
  category: IncidentCategory;
  severity: IncidentSeverity;
  location: { name: string; lat: number; lon: number };
  reported_at: string;
  summary: string;
  verified: boolean;
  source: string;
}

export interface LightingObservation {
  working: boolean | null;
  status_label: string;
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
  crowd: CrowdLevel | null;
  by_time_of_day: { hour: number; score: number; confidence: number }[];
}

export interface HeatZone {
  name: string;
  lat: number;
  lon: number;
  level: number;
}

/* ------------------------------------------------------------------ */
/* Route candidates (planner)                                           */
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
  risk_colors: string[];
  freshness: DataFreshness;
  uncertainty?: number;
  reasons?: string[];
  warnings?: string[];
  model_version?: string;
  segment_ids?: number[];
  high_risk_fraction?: number;
  risk_exposure_m?: number;
  risk_probability?: number;
  confidence_value?: number;
}

export interface GeocodeResult {
  name: string;
  kind: "area" | "facility";
  type: string | null;
  lat: number;
  lon: number;
}

/* ------------------------------------------------------------------ */
/* Admin                                                               */
/* ------------------------------------------------------------------ */

export interface AdminReport {
  report_id: number;
  segment_id: number;
  category: string;
  verification_state: string;
  reported_at: string;
  confidence: number;
}

export interface AdminReportListResponse { reports: AdminReport[]; }

export interface AdminVerificationResponse {
  report_id: number;
  verification_state: string;
}

/* ------------------------------------------------------------------ */
/* Community feed                                                      */
/* ------------------------------------------------------------------ */

export interface CommunityPost {
  id: string;
  kind: "alert" | "route_update" | "photo";
  location: string;
  text: string;
  status: string;
  created_at: string;
}

export interface CommunityFeedResponse { posts: CommunityPost[]; }

export interface CommunityCreateRequest {
  kind: "alert" | "route_update" | "photo";
  location: string;
  text: string;
}

export interface CommunityModerateResponse { id: string; status: "VERIFIED" | "REJECTED"; }

/* ------------------------------------------------------------------ */
/* Reports                                                             */
/* ------------------------------------------------------------------ */

export interface ReportCategoryOption { id: string; label: string; }

export interface ReportSubmission {
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

export interface QuickReportRequest { segment_id: number; category: string; }

export interface QuickReportResponse { report_id: number; }

/* ------------------------------------------------------------------ */
/* Personal safety: contacts / emergency / sharing / guardian / journey */
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

export interface TrustedContactInput {
  name: string;
  relationship: string;
  phone: string;
  role: ContactRole;
}

export interface TrustedContactUpdate {
  name?: string;
  relationship?: string;
  phone?: string;
  role?: ContactRole;
  enabled?: boolean;
}

export interface TrustedContactListResponse { contacts: TrustedContact[]; }

export interface CommunityPostResponse {
  id: string;
  kind: "alert" | "route_update" | "photo";
  location: string;
  text: string;
  status: string;
  created_at: string;
}

export interface CommunityModerateResponse { id: string; status: "VERIFIED" | "REJECTED"; }

export interface RecomputeResponse {
  recomputed: number;
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
  notify_status: string;
  location_sharing: string | null;
}

export interface EmergencyCreateRequest {
  kind: string;
  lat: number | null;
  lon: number | null;
  source_client_id?: string;
}

export interface EmergencyEndRequest { reason: string; }

export interface EmergencyEndResponse {
  session_id: string;
  status: EmergencyStatus;
  ended_at: string;
  end_reason: string;
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

export interface SharingStartRequest {
  kind: SharingKind;
  recipient_ids: number[];
  expires_in_s?: number;
}

export interface SharingLocationUpdate { lat: number; lon: number; }

export interface NotificationEvent {
  id: number;
  type: string;
  channel: string;
  status: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export type GuardianStatus = "ACTIVE" | "COMPLETED" | "CANCELLED" | "ESCALATED";

export interface GuardianSession {
  session_id: string;
  status: GuardianStatus;
  started_at: string;
  ended_at: string | null;
  end_reason: string | null;
  guardian_contact_ids: number[];
  expected_arrival_at: string | null;
  checkin_deadline: string;
  checkin_grace_s: number;
  last_checkin_at: string | null;
  latitude: number | null;
  longitude: number | null;
  last_known_at: string | null;
  deviation_detected: boolean;
  first_deviation_at: string | null;
  escalation_stage: number;
}

export interface GuardianCreateInput {
  guardian_contact_ids: number[];
  expected_arrival_at?: string | null;
  planned_geometry?: [number, number][] | null;
  checkin_grace_s?: number;
}

export interface GuardianEndResult {
  session_id: string;
  status: GuardianStatus;
  ended_at: string;
  end_reason: string;
}

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
/* Privacy center                                                      */
/* ------------------------------------------------------------------ */

export interface PrivacySettings {
  voice_guidance_enabled: boolean;
  voice_language: string;
  discreet_mode_enabled: boolean;
}

export interface PrivacySettingsUpdate {
  voice_guidance_enabled?: boolean;
  voice_language?: string;
  discreet_mode_enabled?: boolean;
}

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
/* Discreet mode                                                       */
/* ------------------------------------------------------------------ */

export interface DiscreetModeSettings {
  client_id: string;
  enabled: boolean;
  quick_sos_gesture: string;
  exit_to_neutral_app: boolean;
  neutral_app_label: string;
  neutral_app_icon: string;
}

export interface DiscreetModeSettingsUpdate {
  enabled?: boolean;
  quick_sos_gesture?: string;
  exit_to_neutral_app?: boolean;
  neutral_app_label?: string;
  neutral_app_icon?: string;
}

/* ------------------------------------------------------------------ */
/* Fake call                                                           */
/* ------------------------------------------------------------------ */

export interface FakeCallSession {
  id: string;
  caller_name: string;
  caller_number: string | null;
  scheduled_at: string;
  status: string;
}

export interface FakeCallInput {
  caller_name: string;
  caller_number?: string | null;
  scheduled_at?: string | null;
}

export interface FakeCallCreate { caller_name: string; caller_number?: string | null; scheduled_at?: string | null; }

export interface FakeCallResponse { session: FakeCallSession; }

export interface FakeCallStatusResponse { session: FakeCallSession; }

/* ------------------------------------------------------------------ */
/* Voice guidance                                                      */
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

export interface VoiceGuidanceStart { route_session_id: string; language?: string; }

export interface VoiceGuidanceResponse { session: VoiceGuidanceStatus; }

/* ------------------------------------------------------------------ */
/* Safety preferences                                                  */
/* ------------------------------------------------------------------ */

export interface SafetyPreferences {
  client_id: string;
  prefer_better_lit: boolean;
  prefer_main_roads: boolean;
  prefer_near_emergency: boolean;
  avoid_known_hazards: boolean;
  avoid_isolated_roads: boolean;
  minimize_walking_time: boolean;
  default_profile: SafetyPreference;
  discreet_mode_enabled: boolean;
  voice_guidance_enabled: boolean;
  voice_language: string;
}

export interface SafetyPreferencesUpdate {
  prefer_better_lit?: boolean;
  prefer_main_roads?: boolean;
  prefer_near_emergency?: boolean;
  avoid_known_hazards?: boolean;
  avoid_isolated_roads?: boolean;
  minimize_walking_time?: boolean;
  default_profile?: SafetyPreference;
  discreet_mode_enabled?: boolean;
  voice_guidance_enabled?: boolean;
  voice_language?: string;
}

/* ------------------------------------------------------------------ */
/* Model traceability                                                  */
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
  cv_models: CVModelInfo[];
}

/* ------------------------------------------------------------------ */
/* Computer vision                                                     */
/* ------------------------------------------------------------------ */

export interface CVModelInfo {
  name: string;
  version: string;
  kind: string;
  framework: string;
  checkpoint_path: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  status: string;
  metrics: Record<string, number>;
  dataset_version: string | null;
  integration: string;
}

export interface CVHealth {
  backend: string;
  loaded: boolean;
  models: CVModelInfo[];
  is_real_inference: boolean;
  note: string;
}

export interface CVListResponse { models: CVModelInfo[]; backend: string; loaded: boolean; is_real_inference: boolean; }

export interface CVPredictRequest { image_base64: string; kind: "cv_classifier" | "cv_detector"; model_name?: string; }

export interface CVPredictResponse {
  kind: string; scores: number[]; detections: Record<string, unknown>[];
  confidence: number | null; model_name: string; model_version: string;
  is_real_inference: boolean; note: string;
}

/* ------------------------------------------------------------------ */
/* Alerts                                                              */
/* ------------------------------------------------------------------ */

export interface AlertResponse {
  id: number;
  category: string;
  severity: IncidentSeverity;
  lat: number;
  lon: number;
  location_name: string | null;
  description: string | null;
  source: string;
  evidence_status: string;
  confidence: number;
  observed_at: string;
  expires_at: string | null;
  created_at: string;
}

export interface AlertListResponse { alerts: AlertResponse[]; }

export interface AlertCreate {
  category: string;
  severity?: "low" | "moderate" | "high" | "critical";
  lat: number; lon: number;
  location_name?: string | null;
  description?: string | null;
  source?: string;
}

/* ------------------------------------------------------------------ */
/* Device auth                                                         */
/* ------------------------------------------------------------------ */

export interface DeviceSessionRequest { client_id: string; }

export interface DeviceSessionResponse { token: string; client_id: string; expires_at: string; }

export interface RevokeSessionResponse { revoked: boolean; }