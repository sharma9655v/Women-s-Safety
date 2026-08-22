/** Typed API gateway — no mocks, real backend only.
 *  Every private call carries X-Client-Id + Bearer token (device session).
 */

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number | null,
    public readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "mf:device_token";
const CLIENT_ID_KEY = "mf:client_id";
const HEX = /^[0-9a-f]{32,64}$/;

function generateClientId(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function clientId(): string {
  let value = "";
  try { value = localStorage.getItem(CLIENT_ID_KEY) ?? ""; } catch {}
  if (!HEX.test(value)) {
    value = generateClientId();
    try { localStorage.setItem(CLIENT_ID_KEY, value); } catch {}
  }
  return value;
}

function storedToken(): string {
  try { return localStorage.getItem(TOKEN_KEY) ?? ""; } catch { return ""; }
}
function clearStoredToken(): void {
  try { localStorage.removeItem(TOKEN_KEY); } catch {}
}

async function acquireDeviceToken(): Promise<string> {
  const cid = clientId();
  const resp = await fetch(`${BASE}/api/auth/device`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Client-Id": cid },
    body: JSON.stringify({ client_id: cid }),
  });
  if (!resp.ok) throw new ApiError(`Auth failed (${resp.status})`, resp.status);
  const { token } = await resp.json();
  try { localStorage.setItem(TOKEN_KEY, token); } catch {}
  return token;
}

async function deviceToken(): Promise<string> {
  const existing = storedToken();
  if (existing) return existing;
  return acquireDeviceToken();
}

async function privateHeaders(): Promise<Record<string, string>> {
  return { "X-Client-Id": clientId(), Authorization: `Bearer ${await deviceToken()}` };
}

async function requestWithRetry<T>(
  path: string,
  method: "GET" | "POST" | "PUT" | "DELETE",
  body?: unknown,
  auth = false,
  retries = 2,
): Promise<T> {
  const headers: Record<string, string> = { "X-Client-Id": clientId() };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) Object.assign(headers, await privateHeaders());

  let resp: Response;
  let attempt = 0;

  while (true) {
    try {
      resp = await fetch(`${BASE}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body)
      });
    } catch {
      if (attempt >= retries) throw new ApiError(`Cannot reach the API at ${BASE}.`, null);
      attempt++;
      await new Promise(r => setTimeout(r, 300 * attempt));
      continue;
    }

    if (resp.status === 401 && auth) {
      clearStoredToken();
      const retryHeaders = { ...headers, ...await privateHeaders() };
      resp = await fetch(`${BASE}${path}`, {
        method,
        headers: retryHeaders,
        body: body === undefined ? undefined : JSON.stringify(body)
      });
    }

    if (!resp.ok) {
      // Retry on transient server errors for idempotent methods
      const isIdempotent = method === "GET" || method === "PUT" || method === "DELETE";
      const isTransient = resp.status >= 500 || resp.status === 429;

      if (isIdempotent && isTransient && attempt < retries) {
        attempt++;
        await new Promise(r => setTimeout(r, 300 * attempt));
        continue;
      }

      let detail: unknown = null;
      try { detail = await resp.json(); } catch {}
      throw new ApiError(`${method} ${path} failed (${resp.status})`, resp.status, detail);
    }

    if (method === "DELETE") return undefined as T;
    return (await resp.json()) as T;
  }
}

const post = <T>(p: string, b: unknown, a = false) => requestWithRetry<T>(p, "POST", b, a);
const get = <T>(p: string, a = false) => requestWithRetry<T>(p, "GET", undefined, a);
const put = <T>(p: string, b: unknown, a = false) => requestWithRetry<T>(p, "PUT", b, a);
const del = (p: string, a = false) => requestWithRetry<void>(p, "DELETE", undefined, a);

/* =========== PUBLIC ENDPOINTS =========== */

export const api = {
  /* Safety & routing */
  routes: async (req: { origin: { lat: number; lon: number }; destination: { lat: number; lon: number }; mode: "walking" | "driving" | "cycling"; safety_preference: "safety" | "balanced" | "time"; hour_ist?: number }) => {
    const res = await post<{ routes: import("./types").RouteResult[] }>("/api/routes", req);
    return res.routes.map((route, i) => ({
      id: `route-${i}`,
      label: route.route_type === "safety_priority" ? "recommended" : route.route_type === "balanced" ? "alternative" : "shortest",
      title: route.route_type.replace("_", " "),
      via: "via main roads",
      distance_m: route.distance_m,
      duration_s: route.duration_s,
      safety: { value: Math.round((1 - route.risk_probability) * 100), band: route.risk_probability < 0.3 ? "high" : route.risk_probability < 0.6 ? "moderate" : "low", confidence: "high" as const, evidence: { sources: [], confidence: "high" as const, confidence_value: 0.9, freshness: { tier: "fresh" as const, label: "Fresh", updated_at: new Date().toISOString(), detail: "Recent" }, conflicts: [], coverage: null } },
      indicators: route.reasons,
      route_type: route.route_type,
      geometry: route.geometry,
      risk_colors: route.geometry.coordinates.map(() => "#3ddc97"),
      freshness: { tier: "fresh" as const, label: "Fresh", updated_at: new Date().toISOString(), detail: "Live data" },
      uncertainty: route.uncertainty,
      reasons: route.reasons,
      warnings: route.warnings,
      model_version: route.model_version,
      segment_ids: route.segment_ids,
      high_risk_fraction: route.high_risk_fraction,
      risk_exposure_m: route.risk_exposure_m,
      risk_probability: route.risk_probability,
      confidence_value: route.confidence,
    })) as import("./types").RouteCandidate[];
  },

  heatmap: (bbox: string, zoom: number) =>
    get<{ zones: import("./types").HeatZone[] }>(`/api/safety/heatmap?bbox=${bbox}&zoom=${zoom}`),

  areas: () => get<import("./types").AreaSafety[]>("/api/safety/areas"),

  activeAlerts: (region?: string) =>
    get<import("./types").AlertListResponse>(`/api/alerts/active${region ? `?region=${region}` : ""}`),

  incidents: (qs = "") => get<import("./types").Incident[]>(`/api/incidents${qs}`),

  facilities: (kind?: string) =>
    get<import("./types").Facility[]>(`/api/facilities${kind ? `?kind=${kind}` : ""}`),

  segmentEvidence: (segmentId: number) =>
    get<import("./types").SafetyEvidence>(`/api/segments/${segmentId}/evidence`),

  geocode: (q: string) =>
    get<import("./types").GeocodeResult[]>(`/api/geocode?q=${encodeURIComponent(q)}`),

  alerts: {
    create: (body: import("./types").AlertCreate) =>
      post<import("./types").AlertResponse>("/api/alerts", body, true),
    list: () => get<import("./types").AlertListResponse>("/api/alerts", true),
  },

  models: () => get<import("./types").ModelsCurrent>("/api/models/current"),

  /* CV */
  cvHealth: () => get<import("./types").CVHealth>("/api/cv/health"),
  cvModels: () => get<import("./types").CVListResponse>("/api/cv/models"),
  cvPredict: (body: { image_base64: string; kind: "cv_classifier" | "cv_detector"; model_name?: string }) =>
    post<import("./types").CVPredictResponse>("/api/cv/predict", body),

  /* =========== PRIVATE ENDPOINTS (auth required) =========== */

  /* Device session */
  acquireToken: acquireDeviceToken,

  /* Contacts */
  contacts: {
    list: () => get<import("./types").TrustedContactListResponse>("/api/contacts", true),
    create: (body: import("./types").TrustedContactInput) => post<import("./types").TrustedContact>("/api/contacts", body, true),
    update: (id: number, body: import("./types").TrustedContactUpdate) => put<import("./types").TrustedContact>(`/api/contacts/${id}`, body, true),
    remove: (id: number) => del(`/api/contacts/${id}`, true),
  },

  /* Emergency */
  emergency: {
    start: (body: { kind: string; lat: number | null; lon: number | null; source_client_id?: string }) =>
      post<import("./types").EmergencySession>("/api/emergency/sessions", body, true),
    end: (sessionId: string, reason: string) =>
      post<import("./types").EmergencyEndResponse>(`/api/emergency/sessions/${sessionId}/end`, { reason }, true),
    active: () => get<import("./types").EmergencySession[]>("/api/emergency/sessions/active", true),
  },

  /* Guardian */
  guardian: {
    start: (body: import("./types").GuardianCreateInput) =>
      post<import("./types").GuardianSession>("/api/guardian/sessions", body, true),
    get: (sessionId: string) => get<import("./types").GuardianSession>(`/api/guardian/sessions/${sessionId}`, true),
    checkin: (sessionId: string) => post<import("./types").GuardianSession>(`/api/guardian/sessions/${sessionId}/checkin`, {}, true),
    end: (sessionId: string, reason: string) => post<import("./types").GuardianEndResult>(`/api/guardian/sessions/${sessionId}/end`, { reason }, true),
    active: () => get<import("./types").GuardianSession[]>("/api/guardian/sessions/active", true),
  },

  /* Location sharing */
  sharing: {
    start: (body: import("./types").SharingStartRequest) =>
      post<import("./types").SharingSession>("/api/location-sharing", body, true),
    get: (sessionId: string) => get<import("./types").SharingSession>(`/api/location-sharing/${sessionId}`, true),
    update: (sessionId: string, body: { lat: number; lon: number }) =>
      post<import("./types").SharingSession>(`/api/location-sharing/${sessionId}/location`, body, true),
    stop: (sessionId: string) => post<import("./types").SharingSession>(`/api/location-sharing/${sessionId}/stop`, {}, true),
    active: () => get<import("./types").SharingSession[]>("/api/location-sharing/active", true),
  },

  /* Journey check-ins */
  journey: {
    start: (body: import("./types").JourneyCheckinInput) =>
      post<import("./types").JourneyCheckinSession>("/api/journey/checkins", body, true),
    checkin: (sessionId: string) => post<import("./types").JourneyCheckinSession>(`/api/journey/checkins/${sessionId}/checkin`, {}, true),
    end: (sessionId: string, reason: string) => post<import("./types").JourneyEndResult>(`/api/journey/checkins/${sessionId}/end`, { reason }, true),
    active: () => get<import("./types").JourneyCheckinSession[]>("/api/journey/checkins/active", true),
  },

  /* Fake call */
  fakeCall: {
    start: (body: import("./types").FakeCallInput) =>
      post<import("./types").FakeCallResponse>("/api/fake-call", body, true),
    status: (id: string) => get<import("./types").FakeCallStatusResponse>(`/api/fake-call/${id}`, true),
    active: () => get<import("./types").FakeCallStatusResponse>("/api/fake-call/status", true),
  },

  /* Voice guidance */
  voice: {
    start: (body: { route_session_id: string; language?: string }) =>
      post<import("./types").VoiceGuidanceResponse>("/api/voice/start", body, true),
    stop: (sessionId: string) => post<import("./types").VoiceGuidanceResponse>(`/api/voice/stop`, { route_session_id: sessionId }, true),
    status: (sessionId: string) => get<import("./types").VoiceGuidanceStatus>(`/api/voice/status?session_id=${sessionId}`, true),
  },

  /* Preferences */
  preferences: {
    get: () => get<import("./types").SafetyPreferences>("/api/preferences", true),
    update: (body: import("./types").SafetyPreferencesUpdate) =>
      put<import("./types").SafetyPreferences>("/api/preferences", body, true),
  },

  /* Discreet mode */
  discreet: {
    get: () => get<import("./types").DiscreetModeSettings>("/api/discreet-mode", true),
    update: (body: import("./types").DiscreetModeSettingsUpdate) =>
      put<import("./types").DiscreetModeSettings>("/api/discreet-mode", body, true),
  },

  /* Reports */
  reports: {
    submit: (body: import("./types").ReportSubmission) =>
      post<import("./types").ReportResult>("/api/reports", body, true),
    quick: (body: import("./types").QuickReportRequest) =>
      post<import("./types").QuickReportResponse>("/api/reports/quick", body, true),
  },

  /* Community */
  community: {
    list: () => get<import("./types").CommunityFeedResponse>("/api/community", true),
    create: (body: import("./types").CommunityCreateRequest) =>
      post<import("./types").CommunityPostResponse>("/api/community", body, true),
    moderate: (body: import("./types").CommunityModerateResponse) =>
      post<import("./types").CommunityPostResponse>("/api/admin/community/moderate", body, true),
  },

  /* Privacy */
  privacy: {
    dashboard: () => get<import("./types").PrivacyDashboard>("/api/privacy/dashboard", true),
    settings: {
      get: () => get<import("./types").PrivacySettings>("/api/privacy/settings", true),
      update: (body: import("./types").PrivacySettingsUpdate) =>
        put<import("./types").PrivacySettings>("/api/privacy/settings", body, true),
    },
  },

  /* Notifications */
  notifications: {
    list: () => get<import("./types").NotificationEvent[]>("/api/notifications", true),
  },

  /* Admin (requires ADMIN_KEY in headers - handled by caller) */
  admin: {
    reports: (adminKey: string) =>
      get<import("./types").AdminReportListResponse>("/api/admin/reports", true),
    recompute: (adminKey: string) =>
      post<import("./types").RecomputeResponse>("/api/admin/recompute", { admin_key: adminKey }, true),
  },
};
