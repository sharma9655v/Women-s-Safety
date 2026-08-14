"use client";

import { ArrowUpDown, Share2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { LiveAlertsList } from "@/app/components/insights/LiveAlertsList";
import type { RouteMapApi } from "@/app/components/map/MapCanvas";
import { MapView } from "@/app/components/map/MapView";
import { RouteCard } from "@/app/components/routes/RouteCard";
import { RouteComparisonDrawer } from "@/app/components/routes/RouteComparisonDrawer";
import { PLACE_SUGGESTIONS, RoutePlanner } from "@/app/components/routes/RoutePlanner";
import { SafetyScoreCard } from "@/app/components/safety/SafetyScoreCard";
import { Button } from "@/app/components/ui/Button";
import { SkeletonCard } from "@/app/components/ui/Skeleton";
import {
  fetchAreaSafety,
  fetchFacilities,
  fetchHeatmapZones,
  fetchIncidents,
  fetchLighting,
  requestRoutes,
} from "@/lib/api";
import type {
  Facility,
  HeatZone,
  Incident,
  LightingObservation,
  RouteCandidate,
  SafetyScore,
} from "@/lib/types";

const DELHI_FALLBACK = { lat: 28.62, lon: 77.24 };

function coordsFor(name: string): { lat: number; lon: number } {
  const match = PLACE_SUGGESTIONS.find((p) => p.label.toLowerCase() === name.trim().toLowerCase());
  return match ? { lat: match.lat, lon: match.lon } : DELHI_FALLBACK;
}

const MODE_MAP: Record<string, "walking" | "driving" | "cycling"> = {
  walking: "walking",
  car: "driving",
  transit: "walking",
  bicycle: "cycling",
};

function ShareTrip({ origin, destination }: { origin: string; destination: string }) {
  const [copied, setCopied] = useState(false);

  const share = async () => {
    const o = coordsFor(origin);
    const d = coordsFor(destination);
    const mapsUrl = `https://www.google.com/maps/dir/${o.lat},${o.lon}/${d.lat},${d.lon}`;
    const text = `I'm heading from ${origin} to ${destination}. Trip link: ${mapsUrl}`;
    if (navigator.share) {
      try {
        await navigator.share({ title: "Share trip", text, url: mapsUrl });
      } catch {
        await navigator.clipboard.writeText(`${text} ${mapsUrl}`);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } else {
      await navigator.clipboard.writeText(`${text} ${mapsUrl}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Button variant="ghost" size="sm" onClick={share}>
      <Share2 className="size-3.5" aria-hidden /> {copied ? "Copied" : "Share"}
    </Button>
  );
}

export default function LivePage() {
  const [routes, setRoutes] = useState<RouteCandidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const [planned, setPlanned] = useState<{
    origin: string;
    destination: string;
  } | null>(null);
  const [areaScore, setAreaScore] = useState<SafetyScore | null>(null);
  const [scoreLoading, setScoreLoading] = useState(true);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [lighting, setLighting] = useState<(LightingObservation & { lat: number; lon: number })[]>(
    [],
  );
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [heatZones, setHeatZones] = useState<HeatZone[]>([]);
  const apiRef = useRef<RouteMapApi | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchAreaSafety()
      .then((area) => {
        if (!cancelled) setAreaScore(area.score);
      })
      .catch(() => {
        if (!cancelled) setAreaScore(null);
      })
      .finally(() => {
        if (!cancelled) setScoreLoading(false);
      });
    fetchIncidents()
      .then((data) => {
        if (!cancelled) setIncidents(data);
      })
      .catch(() => {
        if (!cancelled) setIncidents([]);
      });
    fetchLighting()
      .then((data) => {
        if (!cancelled) setLighting(data);
      })
      .catch(() => {
        if (!cancelled) setLighting([]);
      });
    fetchFacilities()
      .then((data) => {
        if (!cancelled) setFacilities(data);
      })
      .catch(() => {
        if (!cancelled) setFacilities([]);
      });
    fetchHeatmapZones()
      .then((data) => {
        if (!cancelled) setHeatZones(data.zones);
      })
      .catch(() => {
        if (!cancelled) setHeatZones([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const findRoutes = useCallback(
    async (
      origin: string,
      destination: string,
      mode: string,
      hourIst?: number,
      originCoords?: { lat: number; lon: number },
      destCoords?: { lat: number; lon: number },
    ) => {
      setLoading(true);
      setError(null);
      setPlanned({ origin, destination });
      try {
        const plannedRoutes = await requestRoutes({
          origin: originCoords ?? coordsFor(origin),
          destination: destCoords ?? coordsFor(destination),
          mode: MODE_MAP[mode] ?? "walking",
          safety_preference: "safety",
          hour_ist: hourIst,
        });
        setRoutes(plannedRoutes);
        setSelectedId(plannedRoutes[0]?.id ?? null);
        apiRef.current?.flyToRoute(plannedRoutes[0]?.id ?? null);
        const segmentIds = plannedRoutes[0]?.segment_ids;
        if (segmentIds && segmentIds.length > 0) {
          sessionStorage.setItem("mf:last-route-segments", JSON.stringify(segmentIds));
        }
      } catch (e) {
        setRoutes([]);
        setSelectedId(null);
        setError(e instanceof Error ? e.message : "Could not plan a route right now.");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const selectRoute = useCallback((id: string | null) => {
    setSelectedId(id);
    apiRef.current?.flyToRoute(id);
  }, []);

  const hasDemoData =
    incidents.some((i) => i.source === "demo_seed") ||
    lighting.some((l) => l.source === "demo_seed");

  return (
    <div className="flex h-full min-h-0 flex-col lg:flex-row">
      {/* Map */}
      <div id="map" className="relative min-h-[55dvh] flex-1 lg:min-h-0">
        {hasDemoData ? (
          <div className="absolute top-3 left-3 z-[500] flex items-center gap-1.5 rounded-full border border-warning/30 bg-surface/90 px-3 py-1 text-[11px] font-medium text-warning shadow-lg backdrop-blur">
            <span className="size-1.5 rounded-full bg-warning" aria-hidden />
            Demo data — illustrative, not real
          </div>
        ) : null}
        <MapView
          routes={routes}
          incidents={incidents}
          lighting={lighting}
          facilities={facilities}
          heatZones={heatZones}
          selectedRouteId={selectedId}
          onRouteSelect={selectRoute}
          onRouteHover={(id) => setHoveredId(id)}
          apiRef={apiRef}
        />
      </div>

      {/* Right panel */}
      <div className="relative z-10 flex min-h-0 w-full shrink-0 flex-col gap-4 overflow-y-auto border-l border-border bg-surface/30 p-4 backdrop-blur-xl lg:w-[380px]">
        <div id="plan">
          <RoutePlanner onFindRoutes={findRoutes} loading={loading} error={error} />
        </div>

        {loading ? (
          <SkeletonCard rows={3} />
        ) : routes.length > 0 ? (
          <section aria-label="Route options">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-xs font-semibold tracking-wide text-text-muted uppercase">
                {planned ? `${planned.origin} → ${planned.destination}` : "Route options"}
              </h3>
              <div className="flex items-center gap-1">
                {planned ? (
                  <ShareTrip origin={planned.origin} destination={planned.destination} />
                ) : null}
                <Button variant="ghost" size="sm" onClick={() => setCompareOpen(true)}>
                  <ArrowUpDown className="size-3.5" aria-hidden /> Compare
                </Button>
              </div>
            </div>
            <div className="space-y-2.5">
              {routes.map((route) => (
                <RouteCard
                  key={route.id}
                  route={route}
                  selected={selectedId === route.id}
                  hovered={hoveredId === route.id}
                  onSelect={() => selectRoute(route.id)}
                  onHover={(h) => {
                    setHoveredId(h ? route.id : null);
                    apiRef.current?.highlightRoute(h ? route.id : null);
                  }}
                />
              ))}
            </div>
          </section>
        ) : (
          <p className="glass rounded-2xl p-4 text-center text-xs text-text-muted">
            Enter a start point and destination to see route estimates.
          </p>
        )}

        {scoreLoading ? (
          <SkeletonCard rows={2} />
        ) : areaScore ? (
          <SafetyScoreCard
            score={areaScore}
            subtitle="Connaught Place area · Based on available evidence"
          />
        ) : (
          <p className="glass rounded-2xl p-4 text-center text-xs text-text-muted">
            Area safety estimate unavailable right now.
          </p>
        )}

        <div className="h-80 lg:min-h-0 lg:flex-1">
          <LiveAlertsList alerts={incidents} />
        </div>
      </div>

      <RouteComparisonDrawer
        open={compareOpen}
        onClose={() => setCompareOpen(false)}
        routes={routes}
        onChoose={(id) => {
          setSelectedId(id);
          apiRef.current?.flyToRoute(id);
          setCompareOpen(false);
        }}
      />
    </div>
  );
}
