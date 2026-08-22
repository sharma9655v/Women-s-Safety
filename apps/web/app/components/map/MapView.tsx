"use client";

import dynamic from "next/dynamic";
import { type MutableRefObject, useRef, useState } from "react";
import type { Facility, Incident, LightingObservation, RouteCandidate } from "@/lib/types";
import type { MapFilters, RouteMapApi } from "./MapCanvas";
import { MapControls } from "./MapControls";
import { MapFiltersBar } from "./MapFiltersBar";
import { MapModeToggle } from "./MapModeToggle";

const MapCanvas = dynamic(() => import("./MapCanvas").then((m) => m.MapCanvas), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 z-0 flex items-center justify-center bg-background text-sm text-text-muted">
      Loading map…
    </div>
  ),
});

const DEFAULT_FILTERS: MapFilters = {
  incidents: true,
  alerts: true,
  lighting: true,
  facilities: true,
  heatmap: true,
};

export interface MapViewProps {
  routes: RouteCandidate[];
  incidents: Incident[];
  alerts?: Incident[];
  lighting: (LightingObservation & { lat: number; lon: number })[];
  facilities: Facility[];
  heatZones?: { name: string; lat: number; lon: number; level: number }[];
  initialMode?: "2d" | "3d";
  selectedRouteId?: string | null;
  onRouteSelect?: (id: string | null) => void;
  onRouteHover?: (id: string | null) => void;
  apiRef?: MutableRefObject<RouteMapApi | null>;
  className?: string;
}

export function MapView({
  routes,
  incidents,
  alerts = [],
  lighting,
  facilities,
  heatZones = [],
  initialMode = "2d",
  selectedRouteId = null,
  onRouteSelect,
  onRouteHover,
  apiRef: externalApiRef,
  className = "",
}: MapViewProps) {
  const [mode, setMode] = useState<"2d" | "3d">(initialMode);
  const [filters, setFilters] = useState<MapFilters>(DEFAULT_FILTERS);
  const internalApiRef = useRef<RouteMapApi | null>(null);
  const apiRef = externalApiRef ?? internalApiRef;

  return (
    <div className={`relative h-full w-full overflow-hidden bg-background ${className}`}>
      <MapCanvas
        mode={mode}
        routes={routes}
        incidents={incidents}
        alerts={alerts}
        lighting={lighting}
        facilities={facilities}
        heatZones={heatZones}
        filters={filters}
        selectedRouteId={selectedRouteId}
        onSelectRoute={(id) => onRouteSelect?.(id)}
        onSegmentHover={(id) => onRouteHover?.(id)}
        apiRef={apiRef}
      />

      {/* Depth vignette */}
      <div className="map-vignette" aria-hidden />

      {/* Per-segment risk legend — shown with the 3D perspective view */}
      {mode === "3d" ? (
        <div className="absolute bottom-3 left-3 z-[500] rounded-xl border border-border bg-surface/90 px-3 py-2 shadow-lg backdrop-blur-md">
          <p className="mb-1 text-[10px] font-semibold tracking-wide text-text-muted uppercase">
            Per-segment risk estimate
          </p>
          <div className="flex items-center gap-2.5 text-[11px] text-text-secondary">
            <span className="flex items-center gap-1">
              <span className="risk-legend-swatch risk-legend-low" aria-hidden /> Lower
            </span>
            <span className="flex items-center gap-1">
              <span className="risk-legend-swatch risk-legend-mid" aria-hidden /> Moderate
            </span>
            <span className="flex items-center gap-1">
              <span className="risk-legend-swatch risk-legend-high" aria-hidden /> Higher
            </span>
          </div>
          <p className="mt-1 text-[10px] text-text-muted">
            From available evidence — not a guarantee
          </p>
        </div>
      ) : null}

      {/* Filters */}
      <div className="absolute top-3 left-3 z-[500]">
        <MapFiltersBar filters={filters} onChange={setFilters} />
      </div>

      {/* Mode toggle */}
      <div className="absolute right-3 bottom-3 z-[500]">
        <MapModeToggle mode={mode} onChange={setMode} />
      </div>

      {/* Controls */}
      <div className="absolute top-3 right-3 z-[500]">
        <MapControls apiRef={apiRef} mode={mode} />
      </div>

      {/* Attribution */}
      <div className="absolute bottom-1 left-1/2 z-[450] -translate-x-1/2 text-[10px] text-text-muted opacity-70">
        Map data © CARTO · OpenStreetMap
      </div>
    </div>
  );
}
