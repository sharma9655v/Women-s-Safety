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
  lighting: true,
  facilities: true,
  heatmap: true,
  crowd: false,
};

export interface MapViewProps {
  routes: RouteCandidate[];
  incidents: Incident[];
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
