"use client";

import type { ConfidenceLevel, SafetyBand } from "@/lib/types";

interface LiveStatusSectionProps {
  band: SafetyBand | null;
  confidence: ConfidenceLevel | null;
  loading: boolean;
}

export function LiveStatusSection({ band, confidence, loading }: LiveStatusSectionProps) {
  const bandLabel =
    band === "high"
      ? "Lower Risk"
      : band === "moderate"
        ? "Moderate"
        : band === "low"
          ? "Elevated"
          : "Limited Data";

  const bandColor =
    band === "high"
      ? "var(--risk-low)"
      : band === "moderate"
        ? "var(--risk-moderate)"
        : band === "low"
          ? "var(--risk-elevated)"
          : "var(--risk-limited)";

  const confidenceLabel =
    confidence === "high" ? "High" : confidence === "medium" ? "Medium" : confidence === "low" ? "Low" : "—";

  return (
    <div className="live-status-section">
      <div className="live-status-header">
        <span className="text-xs font-bold text-foreground">Live Status</span>
        <span className="text-[11px] text-text-muted">Updated just now</span>
      </div>

      {loading ? (
        <div className="skeleton-shimmer" style={{ height: 40, borderRadius: 8 }} />
      ) : (
        <div className="live-status-row">
          <span className="live-status-dot" style={{ background: bandColor }} aria-hidden />
          <div className="flex-1">
            <p className="text-[11px] text-text-muted">Area Risk Level</p>
            <p className="text-sm font-bold" style={{ color: bandColor }}>
              {bandLabel}
            </p>
          </div>
          <div className="text-right">
            <p className="text-[11px] text-text-muted">Confidence</p>
            <p className="text-sm font-semibold text-foreground">{confidenceLabel}</p>
          </div>
        </div>
      )}
    </div>
  );
}
