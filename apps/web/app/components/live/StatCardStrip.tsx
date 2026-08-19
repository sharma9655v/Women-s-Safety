"use client";

import { ArrowRight, Building2, ShieldAlert, Users } from "lucide-react";
import Link from "next/link";
import { Gauge } from "@/app/components/ui/Gauge";

interface StatCardStripProps {
  safetyScore: number | null;
  safetyBand: string | null;
  confidenceLevel: string | null;
  incidentCount: number;
  facilityCount: number;
  contactCount: number;
  scoreLoading: boolean;
}

export function StatCardStrip({
  safetyScore,
  safetyBand,
  confidenceLevel,
  incidentCount,
  facilityCount,
  contactCount,
  scoreLoading,
}: StatCardStripProps) {
  const bandLabel =
    safetyBand === "high"
      ? "Lower Risk"
      : safetyBand === "moderate"
        ? "Moderate"
        : safetyBand === "low"
          ? "Elevated"
          : "Limited Data";

  const bandColor =
    safetyBand === "high"
      ? "var(--risk-low)"
      : safetyBand === "moderate"
        ? "var(--risk-moderate)"
        : safetyBand === "low"
          ? "var(--risk-elevated)"
          : "var(--risk-limited)";

  return (
    <div className="dashboard-stat-strip">
      {/* Safety Score */}
      <div className="stat-card">
        <div className="flex items-center gap-3 flex-wrap">
          {scoreLoading ? (
            <div className="skeleton-shimmer" style={{ width: 60, height: 60, borderRadius: 30 }} />
          ) : (
            <Gauge value={safetyScore ?? 0} size={60} strokeWidth={5} label={`/ 100`} />
          )}
          <div>
            <p className="stat-card-label">Safety Score (Area)</p>
            <p className="stat-card-value" style={{ color: bandColor, fontSize: "0.9375rem" }}>
              {bandLabel}
            </p>
            <p className="stat-card-sublabel">
              {confidenceLevel ? "Based on recent evidence" : "Estimate from available data"}
            </p>
          </div>
        </div>
        <Link href="/insights" className="stat-card-link">
          View Details <ArrowRight className="size-3" aria-hidden />
        </Link>
      </div>

      {/* Recent Incidents */}
      <div className="stat-card">
        <div
          className="stat-card-icon"
          style={{ background: "color-mix(in srgb, var(--emergency) 12%, transparent)" }}
        >
          <ShieldAlert className="size-4" style={{ color: "var(--emergency)" }} aria-hidden />
        </div>
        <div>
          <p className="stat-card-label">Recent Incidents</p>
          <p className="stat-card-value" style={{ color: "var(--emergency)" }}>
            {incidentCount}
          </p>
          <p className="stat-card-sublabel">Recent community reports</p>
        </div>
        <Link href="/insights" className="stat-card-link">
          View All <ArrowRight className="size-3" aria-hidden />
        </Link>
      </div>

      {/* Nearby Facilities */}
      <div className="stat-card">
        <div
          className="stat-card-icon"
          style={{ background: "color-mix(in srgb, var(--accent) 12%, transparent)" }}
        >
          <Building2 className="size-4" style={{ color: "var(--accent)" }} aria-hidden />
        </div>
        <div>
          <p className="stat-card-label">Nearby Facilities</p>
          <p className="stat-card-value" style={{ color: "var(--accent)" }}>
            {facilityCount}
          </p>
          <p className="stat-card-sublabel">Within 2 km</p>
        </div>
        <Link href="/insights" className="stat-card-link">
          View All <ArrowRight className="size-3" aria-hidden />
        </Link>
      </div>

      {/* Trusted Contacts */}
      <div className="stat-card">
        <div
          className="stat-card-icon"
          style={{ background: "color-mix(in srgb, var(--info) 12%, transparent)" }}
        >
          <Users className="size-4" style={{ color: "var(--info)" }} aria-hidden />
        </div>
        <div>
          <p className="stat-card-label">Trusted Contacts</p>
          <p className="stat-card-value" style={{ color: "var(--info)" }}>
            {contactCount}
          </p>
          <p className="stat-card-sublabel">Enabled for SOS</p>
        </div>
        <Link href="/contacts" className="stat-card-link">
          Manage <ArrowRight className="size-3" aria-hidden />
        </Link>
      </div>
    </div>
  );
}
