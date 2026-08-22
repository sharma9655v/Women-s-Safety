"use client";

import type { MutableRefObject } from "react";
import type { RouteMapApi } from "@/app/components/map/MapCanvas";
import { MapView } from "@/app/components/map/MapView";
import type {
  Facility,
  HeatZone,
  Incident,
  LightingObservation,
  RouteCandidate,
} from "@/lib/types";
import { StatCardStrip } from "./StatCardStrip";

export interface DashboardMapAreaProps {
  routes: RouteCandidate[];
  incidents: Incident[];
  alerts: Incident[];
  lighting: (LightingObservation & { lat: number; lon: number })[];
  facilities: Facility[];
  heatZones: HeatZone[];
  selectedRouteId: string | null;
  onRouteSelect: (id: string | null) => void;
  apiRef: MutableRefObject<RouteMapApi | null>;

  /* Stat card data */
  safetyScore: number | null;
  safetyBand: string | null;
  confidenceLevel: string | null;
  scoreLoading: boolean;
  contactCount: number;
}

export function DashboardMapArea({
  routes,
  incidents,
  alerts,
  lighting,
  facilities,
  heatZones,
  selectedRouteId,
  onRouteSelect,
  apiRef,
  safetyScore,
  safetyBand,
  confidenceLevel,
  scoreLoading,
  contactCount,
}: DashboardMapAreaProps) {
  return (
    <div className="dashboard-map-area">
      {/* Map */}
      <div className="dashboard-map-container">
        {/* Demo data indicator */}
        {incidents.some((i) => i.source === "demo_seed") && (
          <div className="absolute top-3 right-3 z-[500] flex items-center gap-1.5 rounded-full border border-warning/30 bg-surface/90 px-3 py-1 text-[10px] font-medium text-warning shadow-lg backdrop-blur">
            <span className="size-1.5 rounded-full bg-warning" aria-hidden />
            Demo data — illustrative, not real
          </div>
        )}

        {/* Safety disclaimer */}
        <div className="safety-disclaimer">
          <span className="safety-disclaimer-dot" aria-hidden />
          <span>
            Your safety is our priority. We don&apos;t guarantee safety.{" "}
            <a href="/privacy" className="text-primary hover:underline">
              Learn more about privacy and safety policies
            </a>
          </span>
        </div>

        <MapView
          routes={routes}
          incidents={incidents}
          alerts={alerts}
          lighting={lighting}
          facilities={facilities}
          heatZones={heatZones}
          selectedRouteId={selectedRouteId}
          onRouteSelect={onRouteSelect}
          onRouteHover={() => {}}
          apiRef={apiRef}
        />
      </div>

      {/* Bottom stat strip */}
      <StatCardStrip
        safetyScore={safetyScore}
        safetyBand={safetyBand}
        confidenceLevel={confidenceLevel}
        incidentCount={incidents.length}
        facilityCount={facilities.length}
        contactCount={contactCount}
        scoreLoading={scoreLoading}
      />
    </div>
  );
}
