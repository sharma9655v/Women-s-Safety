import type { ConfidenceLevel, SafetyBand, SafetyScore } from "./types";

/** Safety-score semantics.
 *
 * A SafetyScore is an ESTIMATE derived from available evidence — it is never
 * an absolute measure and the UI must never phrase it as a guarantee.
 */

export function bandForScore(value: number): SafetyBand {
  if (value >= 70) return "high";
  if (value >= 45) return "moderate";
  if (value >= 25) return "low";
  return "limited";
}

export const BAND_LABEL: Record<SafetyBand, string> = {
  high: "Good Safety",
  moderate: "Moderate Safety",
  low: "Elevated Risk",
  limited: "Limited Safety Data",
};

export const BAND_VERB: Record<SafetyBand, string> = {
  high: "Good",
  moderate: "Moderate",
  low: "Elevated",
  limited: "Limited",
};

export function confidenceLevel(value: number): ConfidenceLevel {
  if (value >= 0.7) return "high";
  if (value >= 0.4) return "medium";
  return "low";
}

export const CONFIDENCE_LABEL: Record<ConfidenceLevel, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
};

export function scoreFromRisk(riskProbability: number, confidence: number): SafetyScore {
  const value = Math.round((1 - riskProbability) * 100);
  const band = bandForScore(value);
  return {
    value,
    band,
    confidence: confidenceLevel(confidence),
    evidence: {
      sources: [],
      confidence: confidenceLevel(confidence),
      confidence_value: confidence,
      freshness: {
        tier: "unknown",
        label: "Unknown",
        updated_at: null,
        detail: "No recent evidence",
      },
      conflicts: [],
      coverage: 0,
    },
  };
}

export function riskColor(riskProbability: number): string {
  if (riskProbability < 0.04) return "#22c55e";
  if (riskProbability < 0.12) return "#f59e0b";
  return "#f43f5e";
}

/** Honest wording: never "safe route", always "recommended based on evidence". */
export const RECOMMENDED_WORDING = "Recommended based on available evidence";
