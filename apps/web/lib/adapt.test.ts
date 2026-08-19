import { describe, expect, it } from "vitest";
import { adaptRouteResult } from "./adapt";
import type { RouteResult } from "./types";

function makeRoute(overrides: Partial<RouteResult> = {}): RouteResult {
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
    ...overrides,
  };
}

describe("adaptRouteResult", () => {
  it("swaps API [lon, lat] geometry to the UI's [lat, lon] order", () => {
    const candidate = adaptRouteResult(makeRoute(), 0);
    expect(candidate.geometry.coordinates).toEqual([
      [28.62, 77.24],
      [28.63, 77.25],
    ]);
  });

  it("maps bands and confidence without inventing values", () => {
    const candidate = adaptRouteResult(makeRoute({ estimated_safety: 80, confidence: 0.9 }), 0);
    expect(candidate.safety.value).toBe(80);
    expect(candidate.safety.band).toBe("high");
    expect(candidate.safety.confidence).toBe("high");
  });

  it("clamps out-of-range risk probabilities", () => {
    const high = adaptRouteResult(makeRoute({ risk_probability: 1.5 }), 0);
    expect(high.risk_probability).toBe(1);
    const low = adaptRouteResult(makeRoute({ risk_probability: -0.2 }), 0);
    expect(low.risk_probability).toBe(0);
  });

  it("labels the first route recommended and keeps API metadata", () => {
    const candidate = adaptRouteResult(
      makeRoute({ model_version: "deterministic-baseline-v1", segment_ids: [7, 8] }),
      0,
    );
    expect(candidate.label).toBe("recommended");
    expect(candidate.model_version).toBe("deterministic-baseline-v1");
    expect(candidate.segment_ids).toEqual([7, 8]);
    expect(candidate.id).toBe("route-balanced");
  });

  it("never fabricates per-segment evidence the API did not provide", () => {
    const candidate = adaptRouteResult(makeRoute(), 0);
    expect(candidate.safety.evidence.sources).toEqual([]);
    expect(candidate.safety.evidence.freshness.tier).toBe("unknown");
    expect(candidate.freshness.label).toBe("Unknown");
  });
});
