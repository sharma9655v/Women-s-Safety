"use client";

import { ArrowUpDown, ChevronDown, ChevronUp, ExternalLink, Share2, WifiOff } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { FakeCallCard } from "@/app/components/emergency/FakeCallCard";
import { GuardianMode } from "@/app/components/emergency/GuardianMode";
import { JourneyCheckinCard } from "@/app/components/emergency/JourneyCheckinCard";
import { LocationSharing } from "@/app/components/emergency/LocationSharing";
import { VoiceGuidanceCard } from "@/app/components/emergency/VoiceGuidanceCard";
import { LiveAlertsList } from "@/app/components/insights/LiveAlertsList";
import { SafePlaceFinder } from "@/app/components/live/SafePlaceFinder";
import type { RouteMapApi } from "@/app/components/map/MapCanvas";
import { MapView } from "@/app/components/map/MapView";
import { PreferenceSelector } from "@/app/components/routes/PreferenceSelector";
import { RiskierTonightChip } from "@/app/components/routes/RiskierTonightChip";
import { RouteCard } from "@/app/components/routes/RouteCard";
import { RouteComparisonDrawer } from "@/app/components/routes/RouteComparisonDrawer";
import { PLACE_SUGGESTIONS, RoutePlanner } from "@/app/components/routes/RoutePlanner";
import { EvidenceDrawer } from "@/app/components/safety/EvidenceDrawer";
import { SafetyScoreCard } from "@/app/components/safety/SafetyScoreCard";
import { Button } from "@/app/components/ui/Button";
import { SkeletonCard } from "@/app/components/ui/Skeleton";
import {
  fetchAlerts,
  fetchAreaSafety,
  fetchFacilities,
  fetchHeatmapZones,
  fetchIncidents,
  fetchLighting,
  fetchModelsCurrent,
  fetchPreferences,
  requestRoutes,
} from "@/lib/api";
import type {
  Facility,
  HeatZone,
  Incident,
  LightingObservation,
  ModelsCurrent,
  RouteCandidate,
  SafetyPreference,
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
    // OpenStreetMap directions — never Google Maps.
    const mapsUrl = `https://www.openstreetmap.org/directions?from=${o.lat},${o.lon}&to=${d.lat},${d.lon}`;
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

  const o = coordsFor(origin);
  const d = coordsFor(destination);
  const href = `https://www.openstreetmap.org/directions?from=${o.lat},${o.lon}&to=${d.lat},${d.lon}`;

  return (
    <div className="flex items-center gap-1">
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Open trip directions in OpenStreetMap"
        className="inline-flex cursor-pointer items-center gap-1 rounded-lg px-2 py-1 text-xs text-text-secondary transition-colors hover:bg-surface-hover hover:text-foreground"
      >
        <ExternalLink className="size-3.5" aria-hidden /> Open in OSM
      </a>
      <Button variant="ghost" size="sm" onClick={share}>
        <Share2 className="size-3.5" aria-hidden /> {copied ? "Copied" : "Share"}
      </Button>
    </div>
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
  const [plannedCoords, setPlannedCoords] = useState<{
    origin: { lat: number; lon: number } | null;
    destination: { lat: number; lon: number } | null;
    mode: string;
  }>({ origin: null, destination: null, mode: "walking" });
  const [areaScore, setAreaScore] = useState<SafetyScore | null>(null);
  const [scoreLoading, setScoreLoading] = useState(true);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [alerts, setAlerts] = useState<Incident[]>([]);
  const [lighting, setLighting] = useState<(LightingObservation & { lat: number; lon: number })[]>(
    [],
  );
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [heatZones, setHeatZones] = useState<HeatZone[]>([]);
  const apiRef = useRef<RouteMapApi | null>(null);
  const [isOnline, setIsOnline] = useState(true);
  const [offlineWarning, setOfflineWarning] = useState<string | null>(null);
  const [preference, setPreference] = useState<SafetyPreference>("safety");
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [models, setModels] = useState<ModelsCurrent | null>(null);
  const [sheetExpanded, setSheetExpanded] = useState(false);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    setIsOnline(navigator.onLine);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  useEffect(() => {
    const openLinkedSheet = () => {
      if (window.location.hash === "#plan" || window.location.hash === "#guardian") {
        setSheetExpanded(true);
      }
    };
    openLinkedSheet();
    window.addEventListener("hashchange", openLinkedSheet);
    return () => window.removeEventListener("hashchange", openLinkedSheet);
  }, []);

  useEffect(() => {
    if (!isOnline) {
      setOfflineWarning("Offline — location may be outdated. Connect to improve safety data.");
    } else {
      setOfflineWarning(null);
    }
  }, [isOnline]);

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
    fetchAlerts()
      .then((data) => {
        if (!cancelled) setAlerts(data);
      })
      .catch(() => {
        if (!cancelled) setAlerts([]);
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
    fetchPreferences()
      .then((p) => {
        if (!cancelled) setPreference(p.default_profile);
      })
      .catch(() => {
        // keep the default profile
      });
    fetchModelsCurrent()
      .then((m) => {
        if (!cancelled) setModels(m);
      })
      .catch(() => {
        if (!cancelled) setModels(null);
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
      setSheetExpanded(true);
      const o = originCoords ?? coordsFor(origin);
      const d = destCoords ?? coordsFor(destination);
      setPlannedCoords({ origin: o, destination: d, mode: MODE_MAP[mode] ?? "walking" });
      try {
        const plannedRoutes = await requestRoutes({
          origin: o,
          destination: d,
          mode: MODE_MAP[mode] ?? "walking",
          safety_preference: preference,
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
    [preference],
  );

  const selectRoute = useCallback((id: string | null) => {
    setSelectedId(id);
    apiRef.current?.flyToRoute(id);
  }, []);

  const hasDemoData =
    incidents.some((i) => i.source === "demo_seed") ||
    alerts.some((a) => a.source === "demo_seed") ||
    lighting.some((l) => l.source === "demo_seed");

  return (
    <div className="live-layout relative flex h-full min-h-0 flex-col lg:flex-row">
      {/* Map */}
      <div id="map" className="live-map relative min-h-[55dvh] flex-1 lg:min-h-0">
        {hasDemoData ? (
          <div className="absolute top-3 left-3 z-[500] flex items-center gap-1.5 rounded-full border border-warning/30 bg-surface/90 px-3 py-1 text-[11px] font-medium text-warning shadow-lg backdrop-blur">
            <span className="size-1.5 rounded-full bg-warning" aria-hidden />
            Demo data — illustrative, not real
          </div>
        ) : null}
        {isOnline === false && (
          <div className="absolute top-3 left-3 z-[500] flex items-center gap-1.5 rounded-full border border-danger/30 bg-danger/10 px-3 py-1 text-[11px] font-medium text-danger shadow-lg backdrop-blur">
            <WifiOff className="size-3.5" aria-hidden />
            {offlineWarning}
          </div>
        )}
        <div className="absolute bottom-3 left-3 z-[500] rounded-full border border-border bg-surface/90 px-3 py-1 text-[11px] text-text-muted shadow-lg backdrop-blur">
          Coverage: Delhi · limited to areas with reported evidence
        </div>
        <MapView
          routes={routes}
          incidents={incidents}
          alerts={alerts}
          lighting={lighting}
          facilities={facilities}
          heatZones={heatZones}
          selectedRouteId={selectedId}
          onRouteSelect={selectRoute}
          onRouteHover={(id) => setHoveredId(id)}
          apiRef={apiRef}
        />
      </div>

      {/* Route and safety sheet. It becomes a persistent right panel on desktop. */}
      <section
        aria-label="Route and safety details"
        className={`live-side-panel relative z-10 flex min-h-0 w-full shrink-0 flex-col gap-4 overflow-y-auto border-l border-border bg-surface/30 p-4 backdrop-blur-xl lg:w-[380px] ${sheetExpanded ? "is-expanded" : ""}`}
      >
        <button
          type="button"
          className="live-sheet-toggle lg:hidden"
          onClick={() => setSheetExpanded((expanded) => !expanded)}
          aria-expanded={sheetExpanded}
          aria-controls="route-sheet-content"
        >
          <span className="live-sheet-handle" aria-hidden>
            <span />
          </span>
          <span className="min-w-0 flex-1 text-left">
            <span className="block text-[11px] font-semibold tracking-[0.08em] text-text-muted uppercase">
              {planned ? "Route details" : "Plan a route"}
            </span>
            <span className="mt-0.5 block truncate text-sm font-semibold text-foreground">
              {planned
                ? `${planned.origin} → ${planned.destination}`
                : "Choose where you are going"}
            </span>
          </span>
          {sheetExpanded ? (
            <ChevronDown className="size-5 text-text-secondary" aria-hidden />
          ) : (
            <ChevronUp className="size-5 text-text-secondary" aria-hidden />
          )}
        </button>

        <div className="live-sheet-summary lg:hidden">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
            <span className="size-2 rounded-full bg-primary" aria-hidden />
          </span>
          <p>
            {planned
              ? routes.length > 0
                ? `${routes.length} route estimates · tap a card to highlight it on the map`
                : "Getting route estimates from available evidence"
              : "Use your location or type a starting point and destination"}
          </p>
        </div>

        <div id="route-sheet-content" className="live-panel-primary">
          <div id="plan">
            <RoutePlanner onFindRoutes={findRoutes} loading={loading} error={error} />
            <div className="mt-2.5">
              <p className="mb-1.5 text-[10px] font-semibold tracking-wide text-text-muted uppercase">
                Route priority
              </p>
              <PreferenceSelector value={preference} onChange={setPreference} />
            </div>
          </div>
        </div>

        <div className="live-panel-secondary">
          <LocationSharing />

          <div id="guardian">
            <GuardianMode
              plannedGeometry={
                routes.find((r) => r.id === selectedId)?.geometry.coordinates ?? null
              }
            />
          </div>

          <FakeCallCard />

          <JourneyCheckinCard />

          <VoiceGuidanceCard />
        </div>

        <div className="live-panel-primary">
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
                <RiskierTonightChip
                  route={routes.find((r) => r.id === selectedId) ?? null}
                  origin={plannedCoords.origin}
                  destination={plannedCoords.destination}
                  mode={plannedCoords.mode}
                  preference={preference}
                />
                <div className="live-route-card-scroller">
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
              onInspect={() => setEvidenceOpen(true)}
            />
          ) : (
            <p className="glass rounded-2xl p-4 text-center text-xs text-text-muted">
              Area safety estimate unavailable right now.
            </p>
          )}

          {(() => {
            const selected = routes.find((r) => r.id === selectedId);
            const coords = selected?.geometry.coordinates;
            const last = coords && coords.length > 0 ? coords[coords.length - 1] : null;
            if (!last) return null;
            return (
              <SafePlaceFinder
                lat={last[1]}
                lon={last[0]}
                label={planned?.destination ?? "the destination"}
              />
            );
          })()}
        </div>

        <div className="live-panel-secondary">
          <div className="h-80 lg:min-h-0 lg:flex-1">
            <LiveAlertsList alerts={incidents} />
          </div>
        </div>
      </section>

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

      <EvidenceDrawer
        open={evidenceOpen}
        onClose={() => setEvidenceOpen(false)}
        evidence={areaScore?.evidence ?? null}
        models={models}
      />
    </div>
  );
}
