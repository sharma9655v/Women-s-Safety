import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, fetchFakeCallStatus, fetchModelsCurrent, predictCv, requestRoutes } from "./api";
import type { RouteResult } from "./types";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function routeResult(): RouteResult {
  return {
    route_type: "balanced",
    distance_m: 1200,
    duration_s: 900,
    estimated_safety: 60,
    risk_probability: 0.4,
    confidence: 0.5,
    uncertainty: 0.3,
    warnings: [],
    reasons: [],
    model_version: "rules-v1",
    segment_ids: [1, 2, 3],
    high_risk_fraction: 0.1,
    risk_exposure_m: 120,
    geometry: {
      type: "LineString",
      coordinates: [
        [77.24, 28.62],
        [77.25, 28.63],
      ],
    },
  };
}

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  fetchMock.mockReset();
  localStorage.clear();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("requestRoutes", () => {
  it("posts the route request and adapts the response geometry", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ routes: [routeResult()] }));
    const routes = await requestRoutes({
      origin: { lat: 28.62, lon: 77.24 },
      destination: { lat: 28.63, lon: 77.25 },
      mode: "walking",
      safety_preference: "safety",
    });
    const call = fetchMock.mock.calls[0];
    expect(call[0]).toMatch(/^http:\/\/localhost:8000\/api\/routes$/);
    expect(routes[0].geometry.coordinates[0]).toEqual([28.62, 77.24]);
  });
});

describe("device session auth", () => {
  it("acquires a token and sends it as a bearer on private calls", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ token: "token-1" }))
      .mockResolvedValueOnce(jsonResponse([], 200));
    await fetchFakeCallStatus();
    const calls = fetchMock.mock.calls;
    expect(calls[0][0]).toMatch(/\/api\/auth\/device$/);
    expect(calls[1][0]).toMatch(/\/api\/fake-call\/status$/);
    const headers = calls[1][1]?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer token-1");
    expect(headers["X-Client-Id"]).toMatch(/^[0-9a-f]{64}$/);
  });

  it("retries once with a fresh token after a 401", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ token: "token-1" }))
      .mockResolvedValueOnce(jsonResponse({ detail: "expired" }, 401))
      .mockResolvedValueOnce(jsonResponse({ token: "token-2" }))
      .mockResolvedValueOnce(jsonResponse([], 200));
    await fetchFakeCallStatus();
    const calls = fetchMock.mock.calls;
    expect(calls.length).toBe(4);
    const retryHeaders = calls[3][1]?.headers as Record<string, string>;
    expect(retryHeaders.Authorization).toBe("Bearer token-2");
  });

  it("propagates the error when the retry also fails", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ token: "token-1" }))
      .mockResolvedValueOnce(jsonResponse({ detail: "expired" }, 401))
      .mockResolvedValueOnce(jsonResponse({ token: "token-2" }))
      .mockResolvedValueOnce(jsonResponse({ detail: "still expired" }, 401));
    await expect(fetchFakeCallStatus()).rejects.toMatchObject({ status: 401 });
  });
});

describe("error mapping", () => {
  it.each([
    [400, "bad request"],
    [403, "forbidden"],
    [404, "not found"],
    [409, "conflict"],
    [422, "unprocessable"],
    [429, "rate limited"],
    [500, "server error"],
    [503, "unavailable"],
    [504, "timeout"],
  ])("maps HTTP %i to an ApiError with status", async (status, _label) => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: "boom" }, status));
    await expect(fetchModelsCurrent()).rejects.toMatchObject({ status });
  });

  it("surfaces the backend detail message", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ detail: "Unknown or ended journey check-in" }, 404),
    );
    await expect(fetchModelsCurrent()).rejects.toMatchObject({
      message: "Unknown or ended journey check-in",
    });
  });

  it("maps network failures to an ApiError with null status", async () => {
    fetchMock.mockRejectedValue(new TypeError("fetch failed"));
    await expect(fetchModelsCurrent()).rejects.toMatchObject({
      status: null,
      message: "Cannot reach the API at http://localhost:8000.",
    });
  });
});

describe("fetchFakeCallStatus", () => {
  it("returns null when the backend reports no active call", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ token: "t" }))
      .mockResolvedValueOnce(jsonResponse(null, 200));
    expect(await fetchFakeCallStatus()).toBeNull();
  });

  it("returns the latest call when one exists", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ token: "t" })).mockResolvedValueOnce(
      jsonResponse({
        id: "call-1",
        caller_name: "Mom",
        caller_number: null,
        scheduled_at: "2026-08-19T12:00:00+00:00",
        status: "TRIGGERED",
      }),
    );
    const call = await fetchFakeCallStatus();
    expect(call?.id).toBe("call-1");
    expect(call?.status).toBe("TRIGGERED");
  });
});

describe("predictCv", () => {
  it("posts the image payload and kind to /api/cv/predict", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ token: "t" })).mockResolvedValueOnce(
      jsonResponse({
        kind: "cv_classifier",
        scores: [0.9, 0.1],
        detections: [],
        confidence: 0.9,
        model_name: "streetlight-classifier",
        model_version: "v1",
        is_real_inference: false,
        note: "mock",
      }),
    );
    const result = await predictCv({
      image_base64: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
      kind: "cv_classifier",
    });
    const call = fetchMock.mock.calls[1];
    expect(call[0]).toMatch(/\/api\/cv\/predict$/);
    const body = JSON.parse((call[1]?.body as string) ?? "{}");
    expect(body.kind).toBe("cv_classifier");
    expect(body.image_base64).toContain("iVBORw0KGgo");
    expect(result.is_real_inference).toBe(false);
    expect(result.model_name).toBe("streetlight-classifier");
  });
});

describe("ApiError", () => {
  it("carries the HTTP status", () => {
    const err = new ApiError("nope", 503);
    expect(err.status).toBe(503);
    expect(err.name).toBe("ApiError");
  });
});
