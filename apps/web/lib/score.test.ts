import { describe, expect, it } from "vitest";
import { BAND_LABEL, BAND_VERB, bandForScore, confidenceLevel, scoreFromRisk } from "./score";

describe("bandForScore", () => {
  it("maps score bands at the documented boundaries", () => {
    expect(bandForScore(100)).toBe("high");
    expect(bandForScore(70)).toBe("high");
    expect(bandForScore(69)).toBe("moderate");
    expect(bandForScore(45)).toBe("moderate");
    expect(bandForScore(44)).toBe("low");
    expect(bandForScore(25)).toBe("low");
    expect(bandForScore(24)).toBe("limited");
    expect(bandForScore(0)).toBe("limited");
  });

  it("labels every band without ever claiming a guarantee", () => {
    expect(BAND_LABEL.high).toContain("Safety");
    expect(BAND_LABEL.limited).toContain("Limited");
    expect(BAND_VERB.low).toBe("Elevated");
  });
});

describe("confidenceLevel", () => {
  it("maps numeric confidence to levels", () => {
    expect(confidenceLevel(0.7)).toBe("high");
    expect(confidenceLevel(0.69)).toBe("medium");
    expect(confidenceLevel(0.4)).toBe("medium");
    expect(confidenceLevel(0.39)).toBe("low");
  });
});

describe("scoreFromRisk", () => {
  it("derives the score from risk probability and confidence", () => {
    const score = scoreFromRisk(0.1, 0.8);
    expect(score.value).toBe(90);
    expect(score.band).toBe("high");
    expect(score.confidence).toBe("high");
  });

  it("keeps evidence honest when nothing is provided", () => {
    const score = scoreFromRisk(0.9, 0.1);
    expect(score.evidence.sources).toEqual([]);
    expect(score.evidence.freshness.tier).toBe("unknown");
    expect(score.evidence.freshness.label).toBe("Unknown");
  });
});
