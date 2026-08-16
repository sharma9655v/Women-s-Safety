"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { DashboardMapArea } from "@/app/components/live/DashboardMapArea";
import { DashboardRightPanel } from "@/app/components/live/DashboardRightPanel";
import type { RouteMapApi } from "@/app/components/map/MapCanvas";
import { PLACE_SUGGESTIONS } from "@/app/components/routes/RoutePlanner";
import {
  fetchAlerts,
  fetchAreaSafety,
  fetchContacts,
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
};

export default function DashboardPage() {
  /* ---- Map data ---- */
  const [routes, setRoutes] = useState<RouteCandidate[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [alerts, setAlerts] = useState<Incident[]>([]);
  const [lighting, setLighting] = useState<(LightingObservation & { lat: number; lon: number })[]>(
    [],
  );
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [heatZones, setHeatZones] = useState<HeatZone[]>([]);
  const apiRef = useRef<RouteMapApi | null>(null);

  /* ---- Safety data ---- */
  const [areaScore, setAreaScore] = useState<SafetyScore | null>(null);
  const [scoreLoading, setScoreLoading] = useState(true);

  /* ---- Contacts ---- */
  const [contactCount, setContactCount] = useState(0);

  /* ---- Route planning state ---- */
  const [routeLoading, setRouteLoading] = useState(false);

  /* ---- Load all data on mount ---- */
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

    fetchContacts()
      .then((contacts) => {
        if (!cancelled) setContactCount(contacts.length);
      })
      .catch(() => {
        if (!cancelled) setContactCount(0);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  /* ---- Route planning ---- */
  const findRoutes = useCallback(async (origin: string, destination: string, mode: string) => {
    setRouteLoading(true);
    try {
      const o = coordsFor(origin);
      const d = coordsFor(destination);
      const planned = await requestRoutes({
        origin: o,
        destination: d,
        mode: MODE_MAP[mode] ?? "walking",
        safety_preference: "safety",
      });
      setRoutes(planned);
      setSelectedId(planned[0]?.id ?? null);
      apiRef.current?.flyToRoute(planned[0]?.id ?? null);
    } catch {
      setRoutes([]);
      setSelectedId(null);
    } finally {
      setRouteLoading(false);
    }
  }, []);

  /* ---- Quick actions ---- */
  const handleQuickAction = useCallback((actionId: string) => {
    // Navigate to the live page with the relevant feature
    switch (actionId) {
      case "fake-call":
        window.location.href = "/live#plan";
        break;
      case "voice-guide":
        window.location.href = "/live#plan";
        break;
      case "nearby-help":
        window.location.href = "/live";
        break;
      case "check-in":
        window.location.href = "/live#guardian";
        break;
    }
  }, []);

  /* ---- Select route ---- */
  const selectRoute = useCallback((id: string | null) => {
    setSelectedId(id);
    apiRef.current?.flyToRoute(id);
  }, []);

  return (
    <div className="dashboard-layout">
      <DashboardMapArea
        routes={routes}
        incidents={incidents}
        alerts={alerts}
        lighting={lighting}
        facilities={facilities}
        heatZones={heatZones}
        selectedRouteId={selectedId}
        onRouteSelect={selectRoute}
        apiRef={apiRef}
        safetyScore={areaScore?.value ?? null}
        safetyBand={areaScore?.band ?? null}
        confidenceLevel={areaScore?.confidence ?? null}
        scoreLoading={scoreLoading}
        contactCount={contactCount}
      />
      <DashboardRightPanel
        onFindRoutes={findRoutes}
        onQuickAction={handleQuickAction}
        areaRiskBand={areaScore?.band ?? null}
        areaConfidence={areaScore?.confidence ?? null}
        statusLoading={scoreLoading}
        routeLoading={routeLoading}
      />
    </div>
  );
}
