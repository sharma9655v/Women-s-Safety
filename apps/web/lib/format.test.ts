import { afterEach, describe, expect, it, vi } from "vitest";
import { formatDistance, formatDuration, freshnessFromAge, timeAgo } from "./format";

describe("formatDuration", () => {
  it("formats minutes and hours", () => {
    expect(formatDuration(30)).toBe("1 min");
    expect(formatDuration(120)).toBe("2 min");
    expect(formatDuration(3600)).toBe("1 hr");
    expect(formatDuration(5400)).toBe("1 hr 30 min");
  });
});

describe("formatDistance", () => {
  it("formats meters and kilometers", () => {
    expect(formatDistance(400)).toBe("400 m");
    expect(formatDistance(1500)).toBe("1.5 km");
  });
});

describe("timeAgo", () => {
  afterEach(() => vi.restoreAllMocks());

  it("formats relative time", () => {
    vi.setSystemTime(new Date("2026-08-19T12:00:00Z"));
    expect(timeAgo("2026-08-19T11:59:00Z")).toBe("1 min ago");
    expect(timeAgo("2026-08-19T11:00:00Z")).toBe("1 hr ago");
    expect(timeAgo("2026-08-18T12:00:00Z")).toBe("1 day ago");
    expect(timeAgo("2026-08-01T12:00:00Z")).toBe("18 days ago");
  });

  it("never says 0 min ago for future timestamps", () => {
    vi.setSystemTime(new Date("2026-08-19T12:00:00Z"));
    expect(timeAgo("2026-08-19T12:01:00Z")).toBe("1 min ago");
  });
});

describe("freshnessFromAge", () => {
  it("reports unknown for missing age", () => {
    const f = freshnessFromAge(null);
    expect(f.tier).toBe("unknown");
    expect(f.label).toBe("Unknown");
  });

  it("classifies fresh, aging and stale evidence", () => {
    expect(freshnessFromAge(1).tier).toBe("fresh");
    expect(freshnessFromAge(24).tier).toBe("fresh");
    expect(freshnessFromAge(25).tier).toBe("aging");
    expect(freshnessFromAge(24 * 7).tier).toBe("aging");
    expect(freshnessFromAge(24 * 8).tier).toBe("stale");
  });
});
