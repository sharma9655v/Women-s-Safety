import type { DataFreshness, FreshnessTier } from "./types";

export function formatDuration(seconds: number): string {
  const mins = Math.round(seconds / 60);
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m === 0 ? `${h} hr` : `${h} hr ${m} min`;
}

export function formatDistance(meters: number): string {
  if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`;
  return `${Math.round(meters)} m`;
}

export function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.max(1, Math.round(diff / 60000));
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} hr${hours > 1 ? "s" : ""} ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days > 1 ? "s" : ""} ago`;
}

export function freshnessFromAge(ageHours: number | null): DataFreshness {
  if (ageHours === null) {
    return { tier: "unknown", label: "Unknown", updated_at: null, detail: "No recent evidence" };
  }
  if (ageHours <= 24) {
    return { tier: "fresh", label: "Fresh", updated_at: new Date(Date.now() - ageHours * 3600_000).toISOString(), detail: "Updated recently" };
  }
  if (ageHours <= 24 * 7) {
    return { tier: "aging", label: "Aging", updated_at: new Date(Date.now() - ageHours * 3600_000).toISOString(), detail: "Updated a few days ago" };
  }
  return { tier: "stale", label: "Stale", updated_at: new Date(Date.now() - ageHours * 3600_000).toISOString(), detail: "Updated months ago" };
}

export const FRESHNESS_STYLE: Record<FreshnessTier, string> = {
  fresh: "text-safe bg-safe/10 border-safe/20",
  aging: "text-warn bg-warn/10 border-warn/20",
  stale: "text-danger bg-danger/10 border-danger/20",
  unknown: "text-text-low bg-white/5 border-line",
};

export function riskBandLabel(band: import("./types").SafetyBand): string {
  return band === "high" ? "High" : band === "moderate" ? "Moderate" : band === "low" ? "Low" : "Limited";
}

export function riskBandStyle(band: import("./types").SafetyBand): string {
  return band === "high" ? "text-risk-low"
    : band === "moderate" ? "text-risk-moderate"
    : band === "low" ? "text-risk-elevated"
    : "text-risk-limited";
}