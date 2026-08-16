import { adaptRouteResult } from "./adapt";
import { clientId } from "./client-id";
import {
  MOCK_ADMIN_REPORTS,
  MOCK_ALERTS,
  MOCK_AREA_SAFETY,
  MOCK_COMMUNITY,
  MOCK_FACILITIES,
  MOCK_GEOCODE,
  MOCK_HEATMAP,
  MOCK_INCIDENTS,
  MOCK_LIGHTING,
  MOCK_ROUTE_CANDIDATES,
} from "./mock-data";
import type {
  AdminReport,
  AreaSafety,
  CommunityPost,
  CommunityPostInput,
  ContactInput,
  ContactUpdate,
  DiscreetModeSettings,
  EmergencySession,
  Facility,
  FakeCallInput,
  FakeCallSession,
  GeocodeResult,
  GuardianCreateInput,
  GuardianEndResult,
  GuardianSession,
  HeatZone,
  Incident,
  JourneyCheckinInput,
  JourneyCheckinSession,
  JourneyEndResult,
  LightingObservation,
  ModelsCurrent,
  NotificationEvent,
  PrivacyDashboard,
  PrivacySettings,
  ReportResult,
  ReportSubmission,
  RouteCandidate,
  RouteRequest,
  RoutesResponse,
  SafetyEvidence,
  SafetyPreferences,
  SegmentEvidence,
  SharingKind,
  SharingSession,
  TrustedContact,
  VoiceGuidanceStatus,
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

/* ---------------- Device session tokens (Group D auth) ---------------- */

const TOKEN_KEY = "mf:device_token";

function storedToken(): string {
  try {
    return localStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

function clearStoredToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // localStorage unavailable — nothing to clear
  }
}

async function acquireDeviceToken(): Promise<string> {
  const cid = clientId();
  let resp: Response;
  try {
    resp = await fetch(`${apiUrl()}/api/auth/device`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Client-Id": cid },
      body: JSON.stringify({ client_id: cid }),
    });
  } catch {
    throw new ApiError(`Cannot reach the API at ${apiUrl()}.`, null);
  }
  if (!resp.ok) {
    throw await parseError(resp);
  }
  const body = (await resp.json()) as { token: string };
  try {
    localStorage.setItem(TOKEN_KEY, body.token);
  } catch {
    // token lives for this tab only
  }
  return body.token;
}

async function deviceToken(): Promise<string> {
  const existing = storedToken();
  if (existing) return existing;
  return acquireDeviceToken();
}

/** Headers for private endpoints: the bearer token plus the pseudonymous id. */
async function privateHeaders(): Promise<Record<string, string>> {
  const token = await deviceToken();
  return { "X-Client-Id": clientId(), Authorization: `Bearer ${token}` };
}

async function request<T>(
  path: string,
  method: "GET" | "POST" | "PUT" | "DELETE",
  body?: unknown,
  auth = false,
): Promise<T> {
  const makeRequest = async (): Promise<Response> => {
    const headers: Record<string, string> = { "X-Client-Id": clientId() };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (auth) Object.assign(headers, await privateHeaders());
    return fetch(`${apiUrl()}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  };
  let resp: Response;
  try {
    resp = await makeRequest();
  } catch {
    throw new ApiError(`Cannot reach the API at ${apiUrl()}.`, null);
  }
  if (resp.status === 401 && auth) {
    // The stored token was revoked or expired: acquire a fresh one and retry.
    clearStoredToken();
    try {
      resp = await makeRequest();
    } catch {
      throw new ApiError(`Cannot reach the API at ${apiUrl()}.`, null);
    }
  }
  if (!resp.ok) {
    throw await parseError(resp);
  }
  if (method === "DELETE") {
    return undefined as T;
  }
  return (await resp.json()) as T;
}

function postJson<T>(path: string, body: unknown, auth = false): Promise<T> {
  return request<T>(path, "POST", body, auth);
}

function getJson<T>(path: string, auth = false): Promise<T> {
  return request<T>(path, "GET", undefined, auth);
}

function putJson<T>(path: string, body: unknown, auth = false): Promise<T> {
  return request<T>(path, "PUT", body, auth);
}

function deleteJson(path: string, auth = false): Promise<void> {
  return request<void>(path, "DELETE", undefined, auth);
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

/** Raw response of GET /api/segments/{segment_id}/evidence (backend contract). */
interface SegmentEvidenceSourceSummary {
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

interface SegmentEvidenceResponse {
  segment_id: number;
  total_observations: number;
  overall_freshness: number;
  overall_confidence: number;
  conflicts: string[];
  by_type: Record<string, SegmentEvidenceSourceSummary>;
  model_version: string;
}

function evidenceTier(score: number): "fresh" | "aging" | "stale" | "unknown" {
  if (score <= 0) return "unknown";
  if (score < 0.4) return "stale";
  if (score < 0.75) return "aging";
  return "fresh";
}

function tierLabel(tier: "fresh" | "aging" | "stale" | "unknown"): string {
  return tier === "unknown"
    ? "Unknown"
    : tier === "fresh"
      ? "Fresh"
      : tier === "aging"
        ? "Aging"
        : "Stale";
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
  const typeEntries = Object.entries(raw.by_type);
  const overallTier = evidenceTier(raw.overall_freshness);
  return {
    sources: typeEntries.map(([type, s]) => ({
      id: `type-${type}`,
      name: type.replace(/_/g, " "),
      kind: "community" as const,
      reliability: s.score,
      freshness: {
        tier: evidenceTier(s.freshness),
        label: tierLabel(evidenceTier(s.freshness)),
        updated_at: null,
        detail: `${s.count} observation${s.count !== 1 ? "s" : ""}${
          s.distinct_source_types > 0 ? ` · ${s.distinct_source_types} source type(s)` : ""
        }`,
      },
    })),
    confidence:
      raw.overall_confidence >= 0.75 ? "high" : raw.overall_confidence >= 0.45 ? "medium" : "low",
    confidence_value: raw.overall_confidence,
    freshness: {
      tier: overallTier,
      label: tierLabel(overallTier),
      updated_at: null,
      detail:
        raw.total_observations === 0
          ? "No evidence yet — limited safety data"
          : `Aggregated freshness score ${Math.round(raw.overall_freshness * 100)}%`,
    },
    conflicts: [
      ...typeEntries
        .filter(([, s]) => s.conflicts)
        .map(([type]) => ({
          observation_type: type,
          detail: "Conflicting observations in this category",
        })),
      ...raw.conflicts.map((detail) => ({ observation_type: "mixed", detail })),
    ],
    // The API does not report a coverage share; do not invent one.
    coverage: null,
  };
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

/** Facilities inside a small box around a point (used by the safe-place finder). */
export async function fetchFacilitiesNear(
  lat: number,
  lon: number,
  radiusKm = 2,
): Promise<Facility[]> {
  const dLat = radiusKm / 110.574;
  const dLon = radiusKm / (111.32 * Math.max(0.1, Math.cos((lat * Math.PI) / 180)));
  const q = `min_lon=${(lon - dLon).toFixed(6)}&min_lat=${(lat - dLat).toFixed(6)}&max_lon=${(lon + dLon).toFixed(6)}&max_lat=${(lat + dLat).toFixed(6)}&limit=60`;
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 250));
    return MOCK_FACILITIES.slice(0, 8);
  }
  return getJson<Facility[]>(`/api/facilities?${q}`);
}

export async function fetchCommunity(): Promise<CommunityPost[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200));
    return MOCK_COMMUNITY;
  }
  const resp = await getJson<{ posts: CommunityPost[] }>("/api/community");
  return resp.posts;
}

export async function submitCommunityPost(input: CommunityPostInput): Promise<CommunityPost> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 500));
    return {
      id: `mock-${Date.now()}`,
      kind: input.kind,
      location: input.location,
      text: input.text,
      status: "PENDING",
      created_at: new Date().toISOString(),
    };
  }
  return postJson<CommunityPost>("/api/community", input);
}

export async function fetchAreaSafety(): Promise<AreaSafety> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300));
    return MOCK_AREA_SAFETY;
  }
  return getJson<AreaSafety>("/api/safety/area?name=connaught-place");
}

export async function fetchAreaComparisons(): Promise<AreaSafety[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300));
    return [MOCK_AREA_SAFETY];
  }
  return getJson<AreaSafety[]>("/api/safety/areas");
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

/* ---------------- Evidence engine ---------------- */

export async function fetchSegmentEvidenceStats(segmentId: number): Promise<SegmentEvidence> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300));
    return {
      segment_id: segmentId,
      total_observations: 0,
      overall_freshness: 0,
      overall_confidence: 0,
      conflicts: [],
      by_type: {},
      model_version: "mock-v0",
    };
  }
  return getJson<SegmentEvidence>(`/api/segments/${segmentId}/evidence`);
}

/* ---------------- Geocode ---------------- */

export async function fetchGeocode(query: string, limit = 6): Promise<GeocodeResult[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200));
    const q = query.toLowerCase();
    return MOCK_GEOCODE.filter(
      (r) => r.name.toLowerCase().includes(q) || r.type?.toLowerCase().includes(q),
    ).slice(0, limit);
  }
  const resp = await getJson<{ results: GeocodeResult[] }>(
    `/api/geocode?q=${encodeURIComponent(query)}&limit=${limit}`,
  );
  return resp.results;
}

/* ---------------- Admin review ---------------- */

export async function fetchAdminReports(adminKey: string): Promise<AdminReport[]> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 250));
    return MOCK_ADMIN_REPORTS;
  }
  const resp = await fetch(`${apiUrl()}/api/admin/reports`, {
    headers: { "X-Admin-Key": adminKey },
  });
  if (!resp.ok) {
    throw await parseError(resp);
  }
  const body = (await resp.json()) as { reports: AdminReport[] };
  return body.reports;
}

export async function adminSetVerification(
  reportId: number,
  state: "verify" | "reject",
  adminKey: string,
): Promise<void> {
  if (USE_MOCK) return;
  const resp = await fetch(`${apiUrl()}/api/admin/reports/${reportId}/${state}`, {
    method: "POST",
    headers: { "X-Admin-Key": adminKey },
  });
  if (!resp.ok) {
    throw await parseError(resp);
  }
}

export async function adminModerateCommunityPost(
  postId: string,
  state: "verify" | "reject",
  adminKey: string,
): Promise<void> {
  if (USE_MOCK) return;
  const resp = await fetch(`${apiUrl()}/api/admin/community/${postId}/${state}`, {
    method: "POST",
    headers: { "X-Admin-Key": adminKey },
  });
  if (!resp.ok) {
    throw await parseError(resp);
  }
}

/* ---------------- Personal safety (Phase 9) ---------------- */

export async function fetchContacts(): Promise<TrustedContact[]> {
  const resp = await getJson<{ contacts: TrustedContact[] }>("/api/contacts", true);
  return resp.contacts;
}

export async function createContact(input: ContactInput): Promise<TrustedContact> {
  return postJson<TrustedContact>("/api/contacts", input, true);
}

export async function updateContact(id: number, input: ContactUpdate): Promise<TrustedContact> {
  return putJson<TrustedContact>(`/api/contacts/${id}`, input, true);
}

export async function deleteContact(id: number): Promise<void> {
  await deleteJson(`/api/contacts/${id}`, true);
}

export async function fetchActiveEmergency(): Promise<EmergencySession | null> {
  return getJson<EmergencySession | null>("/api/emergency/sessions/active", true);
}

export async function startEmergency(
  latitude: number,
  longitude: number,
  notified_contact_ids: number[],
): Promise<EmergencySession> {
  return postJson<EmergencySession>(
    "/api/emergency/sessions",
    { latitude, longitude, notified_contact_ids },
    true,
  );
}

export async function endEmergency(sessionId: string, reason: string): Promise<void> {
  await postJson<{ session_id: string }>(
    `/api/emergency/sessions/${sessionId}/end`,
    {
      reason,
    },
    true,
  );
}

export async function updateEmergencyLocation(
  sessionId: string,
  latitude: number,
  longitude: number,
): Promise<EmergencySession> {
  return postJson<EmergencySession>(
    `/api/emergency/sessions/${sessionId}/location`,
    { latitude, longitude },
    true,
  );
}

export async function fetchActiveSharing(): Promise<SharingSession | null> {
  return getJson<SharingSession | null>("/api/location-sharing/active", true);
}

export async function startSharing(
  kind: SharingKind,
  ttl_s: number,
  recipient_ids: number[],
): Promise<SharingSession> {
  return postJson<SharingSession>("/api/location-sharing", { kind, ttl_s, recipient_ids }, true);
}

export async function stopSharing(sessionId: string): Promise<void> {
  await postJson<{ session_id: string }>(`/api/location-sharing/${sessionId}/stop`, {}, true);
}

export async function updateSharingLocation(
  sessionId: string,
  latitude: number,
  longitude: number,
): Promise<SharingSession> {
  return postJson<SharingSession>(
    `/api/location-sharing/${sessionId}/location`,
    { latitude, longitude },
    true,
  );
}

export async function fetchNotifications(limit = 20): Promise<NotificationEvent[]> {
  const resp = await getJson<{ notifications: NotificationEvent[] }>(
    `/api/notifications?limit=${limit}`,
    true,
  );
  return resp.notifications;
}

/* ---------------- Privacy center (Feature Group X) ---------------- */

export async function fetchPrivacySettings(): Promise<PrivacySettings> {
  return getJson<PrivacySettings>("/api/privacy/settings", true);
}

export async function updatePrivacySettings(
  input: Partial<PrivacySettings>,
): Promise<PrivacySettings> {
  return putJson<PrivacySettings>("/api/privacy/settings", input, true);
}

export async function fetchPrivacyDashboard(): Promise<PrivacyDashboard> {
  return getJson<PrivacyDashboard>("/api/privacy/dashboard", true);
}

/* ---------------- Guardian journeys (Phase 10) ---------------- */

export async function fetchActiveGuardian(): Promise<GuardianSession | null> {
  return getJson<GuardianSession | null>("/api/guardian/sessions/active", true);
}

export async function fetchGuardian(sessionId: string): Promise<GuardianSession> {
  return getJson<GuardianSession>(`/api/guardian/sessions/${sessionId}`, true);
}

export async function startGuardian(input: GuardianCreateInput): Promise<GuardianSession> {
  return postJson<GuardianSession>("/api/guardian/sessions", input, true);
}

export async function updateGuardianLocation(
  sessionId: string,
  latitude: number,
  longitude: number,
): Promise<GuardianSession> {
  return postJson<GuardianSession>(
    `/api/guardian/sessions/${sessionId}/location`,
    { latitude, longitude },
    true,
  );
}

export async function checkInGuardian(sessionId: string): Promise<GuardianSession> {
  return postJson<GuardianSession>(`/api/guardian/sessions/${sessionId}/checkin`, {}, true);
}

export async function endGuardian(
  sessionId: string,
  reason: "arrived" | "cancelled",
): Promise<GuardianEndResult> {
  return postJson<GuardianEndResult>(`/api/guardian/sessions/${sessionId}/end`, { reason }, true);
}

/* ---------------- Safety preferences (Feature Group Q) ---------------- */

export async function fetchPreferences(): Promise<SafetyPreferences> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200));
    return {
      client_id: "mock-client",
      prefer_better_lit: true,
      prefer_main_roads: true,
      prefer_near_emergency: true,
      avoid_known_hazards: true,
      avoid_isolated_roads: false,
      minimize_walking_time: false,
      default_profile: "balanced",
      discreet_mode_enabled: false,
      voice_guidance_enabled: true,
      voice_language: "en",
    };
  }
  return getJson<SafetyPreferences>("/api/preferences", true);
}

/** The backend update is a full replacement — send every field. */
export async function updatePreferences(input: SafetyPreferences): Promise<SafetyPreferences> {
  if (USE_MOCK) return input;
  return putJson<SafetyPreferences>("/api/preferences", input, true);
}

/* ---------------- Discreet mode (Feature Group R) ---------------- */

export async function fetchDiscreetMode(): Promise<DiscreetModeSettings> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200));
    return {
      client_id: "mock-client",
      enabled: false,
      quick_sos_gesture: "triple_tap",
      exit_to_neutral_app: true,
      neutral_app_label: "Weather",
      neutral_app_icon: "cloud",
    };
  }
  return getJson<DiscreetModeSettings>("/api/discreet-mode", true);
}

export async function updateDiscreetMode(
  input: Partial<DiscreetModeSettings>,
): Promise<DiscreetModeSettings> {
  if (USE_MOCK) return { ...(await fetchDiscreetMode()), ...input };
  return putJson<DiscreetModeSettings>("/api/discreet-mode", input, true);
}

/* ---------------- Fake call (Feature Group T) ---------------- */

export async function startFakeCall(input: FakeCallInput): Promise<FakeCallSession> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300));
    return {
      id: `mock-${Date.now()}`,
      caller_name: input.caller_name,
      caller_number: input.caller_number ?? null,
      scheduled_at: new Date().toISOString(),
      status: "TRIGGERED",
    };
  }
  return postJson<FakeCallSession>("/api/fake-call", input, true);
}

export async function fetchFakeCall(callId: string): Promise<FakeCallSession> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200));
    return {
      id: callId,
      caller_name: "Mom",
      caller_number: null,
      scheduled_at: new Date().toISOString(),
      status: "TRIGGERED",
    };
  }
  return getJson<FakeCallSession>(`/api/fake-call/${callId}`, true);
}

/* ---------------- Voice guidance (Feature Group U) ---------------- */

export async function startVoiceGuidance(
  language = "en",
  routeSessionId?: string | null,
): Promise<VoiceGuidanceStatus> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200));
    return {
      session_id: "mock-voice",
      client_id: "mock-client",
      route_session_id: routeSessionId ?? null,
      language,
      active: true,
      started_at: new Date().toISOString(),
      ended_at: null,
    };
  }
  return postJson<VoiceGuidanceStatus>(
    "/api/voice/start",
    { language, route_session_id: routeSessionId ?? null },
    true,
  );
}

export async function stopVoiceGuidance(): Promise<VoiceGuidanceStatus> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 200));
    return {
      session_id: "mock-voice",
      client_id: "mock-client",
      route_session_id: null,
      language: "en",
      active: false,
      started_at: new Date().toISOString(),
      ended_at: new Date().toISOString(),
    };
  }
  return postJson<VoiceGuidanceStatus>("/api/voice/stop", {}, true);
}

export async function fetchVoiceGuidanceStatus(): Promise<VoiceGuidanceStatus> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 150));
    return {
      session_id: "",
      client_id: "mock-client",
      route_session_id: null,
      language: "en",
      active: false,
      started_at: "",
      ended_at: "",
    };
  }
  return getJson<VoiceGuidanceStatus>("/api/voice/status", true);
}

/* ---------------- Journey check-ins (Feature Group V) ---------------- */

export async function fetchActiveJourneyCheckin(): Promise<JourneyCheckinSession | null> {
  if (USE_MOCK) return null;
  return getJson<JourneyCheckinSession | null>("/api/journey/checkins/active", true);
}

export async function startJourneyCheckin(
  input: JourneyCheckinInput,
): Promise<JourneyCheckinSession> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300));
    return {
      session_id: "mock-journey",
      status: "ACTIVE",
      started_at: new Date().toISOString(),
      ended_at: null,
      end_reason: null,
      destination_name: input.destination_name,
      destination_lat: input.destination_lat,
      destination_lon: input.destination_lon,
      expected_arrival_at: input.expected_arrival_at ?? null,
      checkin_interval_s: input.checkin_interval_s ?? 900,
      checkin_grace_s: input.checkin_grace_s ?? 300,
      last_checkin_at: new Date().toISOString(),
      next_checkin_at: new Date(Date.now() + 900_000).toISOString(),
      contact_ids: input.contact_ids,
      escalation_stage: 0,
      notified_stage: 0,
      latitude: null,
      longitude: null,
      last_known_at: null,
    };
  }
  return postJson<JourneyCheckinSession>("/api/journey/checkins", input, true);
}

export async function checkinJourney(sessionId: string): Promise<JourneyCheckinSession> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 300));
    const active = await fetchActiveJourneyCheckin();
    if (!active) throw new Error("No active check-in journey.");
    return {
      ...active,
      last_checkin_at: new Date().toISOString(),
      next_checkin_at: new Date(Date.now() + 900_000).toISOString(),
    };
  }
  return postJson<JourneyCheckinSession>(`/api/journey/checkins/${sessionId}/checkin`, {}, true);
}

export async function endJourneyCheckin(
  sessionId: string,
  reason: "arrived" | "cancelled",
): Promise<JourneyEndResult> {
  if (USE_MOCK) {
    return {
      session_id: sessionId,
      status: reason === "arrived" ? "COMPLETED" : "CANCELLED",
      ended_at: new Date().toISOString(),
      end_reason: reason,
    };
  }
  return postJson<JourneyEndResult>(`/api/journey/checkins/${sessionId}/end`, { reason }, true);
}

/* ---------------- Model traceability ---------------- */

export async function fetchModelsCurrent(): Promise<ModelsCurrent> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 150));
    return {
      risk_model: "rules-v1 (deterministic)",
      evidence_model: "evidence-fusion-v1",
      dataset_versions: ["demo-evidence-2026-07"],
      ml_gate: {
        open: false,
        verified_observations: 0,
        span_days: null,
        min_verified_observations: 1000,
        min_span_days: 90,
      },
    };
  }
  return getJson<ModelsCurrent>("/api/models/current");
}

/* ---------------- Device session (auth) ---------------- */

/** Revoke the current device session and forget the local pseudonymous identity. */
export async function revokeDeviceSession(): Promise<void> {
  if (USE_MOCK) return;
  try {
    await postJson<{ revoked: boolean }>("/api/auth/revoke", {}, true);
  } finally {
    clearStoredToken();
    try {
      localStorage.removeItem("mf:client_id");
    } catch {
      // nothing to clear
    }
  }
}
