"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster";
import { type MutableRefObject, useEffect, useRef } from "react";
import { timeAgo } from "@/lib/format";
import { BAND_LABEL, bandForScore } from "@/lib/score";
import type { Facility, Incident, LightingObservation, RouteCandidate } from "@/lib/types";

declare global {
  interface Window {
    __mfFitted?: boolean;
  }
}

export interface RouteMapApi {
  flyToRoute: (id: string | null) => void;
  highlightRoute: (id: string | null) => void;
  zoomIn: () => void;
  zoomOut: () => void;
  resetView: () => void;
  tiltBy: (deg: number) => void;
  rotateBy: (deg: number) => void;
  resetTransform: () => void;
}

export interface MapFilters {
  incidents: boolean;
  lighting: boolean;
  facilities: boolean;
  heatmap: boolean;
  crowd: boolean;
}

const TILE_URL = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const DELHI: L.LatLngExpression = [28.62, 77.24];

function incidentIcon(severity: string): L.DivIcon {
  return L.divIcon({
    className: "",
    html: `<span class="incident-marker incident-marker-${severity}" role="img" aria-label="Incident: ${severity} severity"></span>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

function lightingIcon(state: "working" | "uncertain" | "out"): L.DivIcon {
  return L.divIcon({
    className: "",
    html: `<span class="lighting-marker lighting-marker-${state}"></span>`,
    iconSize: [11, 11],
    iconAnchor: [5.5, 5.5],
  });
}

const FACILITY_GLYPH: Record<string, string> = {
  police: "P",
  hospital: "+",
  fire_station: "F",
  pharmacy: "X",
  transit_stop: "T",
};

function facilityIcon(type: string): L.DivIcon {
  const glyph = FACILITY_GLYPH[type] ?? "•";
  return L.divIcon({
    className: "",
    html: `<span class="facility-marker facility-marker-${type}">${glyph}</span>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
}

function heatColor(level: number): string {
  if (level < 0.35) return "#06d6a0";
  if (level < 0.5) return "#ffa726";
  return "#ff4757";
}

function riskColor(risk: number): string {
  if (risk < 0.04) return "#06d6a0";
  if (risk < 0.12) return "#ffa726";
  return "#ff4757";
}

interface MapCanvasProps {
  mode: "2d" | "3d";
  routes: RouteCandidate[];
  incidents: Incident[];
  lighting: (LightingObservation & { lat: number; lon: number })[];
  facilities: Facility[];
  heatZones?: { name: string; lat: number; lon: number; level: number }[];
  filters: MapFilters;
  selectedRouteId: string | null;
  onSelectRoute: (id: string | null) => void;
  onSegmentHover: (routeId: string | null) => void;
  apiRef: MutableRefObject<RouteMapApi | null>;
}

export function MapCanvas({
  mode,
  routes,
  incidents,
  lighting,
  facilities,
  heatZones = [],
  filters,
  selectedRouteId,
  onSelectRoute,
  onSegmentHover,
  apiRef,
}: MapCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const routeLinesRef = useRef<Map<string, L.Polyline[]>>(new Map());
  const groupsRef = useRef<{
    incident: L.MarkerClusterGroup;
    lighting: L.LayerGroup;
    facility: L.LayerGroup;
    heat: L.LayerGroup;
  } | null>(null);

  // --- init once ---
  useEffect(() => {
    const container = containerRef.current;
    if (!container || mapRef.current) return;

    const map = L.map(container, {
      zoomControl: false,
      attributionControl: true,
      minZoom: 3,
      maxZoom: 19,
    });
    map.setView(DELHI, 13);

    L.tileLayer(TILE_URL, {
      attribution: '&copy; <a href="https://carto.com/attributions">CARTO</a> &copy; OpenStreetMap',
      subdomains: "abcd",
      maxZoom: 20,
    }).addTo(map);

    const incident = L.markerClusterGroup({
      showCoverageOnHover: false,
      maxClusterRadius: 42,
      spiderfyOnMaxZoom: true,
    });
    const lightingGroup = L.layerGroup();
    const facilityGroup = L.layerGroup();
    const heatGroup = L.layerGroup();
    map.addLayer(incident);
    map.addLayer(lightingGroup);
    map.addLayer(facilityGroup);
    map.addLayer(heatGroup);
    groupsRef.current = {
      incident,
      lighting: lightingGroup,
      facility: facilityGroup,
      heat: heatGroup,
    };

    mapRef.current = map;

    const highlightRoute = (id: string | null) => {
      routeLinesRef.current.forEach((lines, routeId) => {
        const active = routeId === id;
        for (const line of lines) {
          line.setStyle({ weight: active ? 6 : 4, opacity: active ? 1 : 0.75 });
          line.getElement()?.classList.toggle("route-selected", active);
        }
      });
    };

    apiRef.current = {
      flyToRoute: (id) => {
        const lines = id ? routeLinesRef.current.get(id) : undefined;
        if (lines?.length) {
          map.fitBounds(L.latLngBounds(lines.flatMap((l) => l.getLatLngs() as L.LatLng[])), {
            padding: [60, 60],
          });
        } else {
          map.setView(DELHI, 13);
        }
      },
      highlightRoute,
      zoomIn: () => map.setZoom(Math.min(map.getZoom() + 1, 19)),
      zoomOut: () => map.setZoom(Math.max(map.getZoom() - 1, 3)),
      resetView: () => map.setView(DELHI, 13),
      tiltBy: (deg) => {
        const tilt = Number.parseFloat(container.style.getPropertyValue("--map-tilt") || "52");
        container.style.setProperty("--map-tilt", `${Math.max(20, Math.min(75, tilt + deg))}deg`);
      },
      rotateBy: (deg) => {
        const rot = Number.parseFloat(container.style.getPropertyValue("--map-rotate") || "0");
        container.style.setProperty("--map-rotate", `${(rot + deg) % 360}deg`);
      },
      resetTransform: () => {
        container.style.setProperty("--map-tilt", "52deg");
        container.style.setProperty("--map-rotate", "0deg");
        container.style.setProperty("--map-scale", "1.35");
        map.setView(DELHI, 13);
      },
    };

    return () => {
      routeLinesRef.current.clear();
      map.remove();
      mapRef.current = null;
      apiRef.current = null;
    };
  }, [apiRef]);

  // --- 2D/3D mode ---
  useEffect(() => {
    const container = containerRef.current;
    const map = mapRef.current;
    if (!container || !map) return;
    const is3d = mode === "3d";
    container.classList.toggle("is-3d", is3d);
    if (is3d) {
      map.dragging.disable();
      map.scrollWheelZoom.disable();
      container.style.setProperty("--map-tilt", "52deg");
      container.style.setProperty("--map-rotate", "0deg");
      container.style.setProperty("--map-scale", "1.35");
    } else {
      map.dragging.enable();
      map.scrollWheelZoom.enable();
    }
  }, [mode]);

  // --- routes ---
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    routeLinesRef.current.forEach((lines) => {
      lines.forEach((l) => {
        l.remove();
      });
    });
    routeLinesRef.current.clear();

    const legend = (c: RouteCandidate) => {
      const score = c.safety.value;
      const band = BAND_LABEL[bandForScore(score)];
      const conf = c.safety.confidence;
      const indicators = c.indicators.join(" · ");
      return (
        `<div class="segment-tooltip">` +
        `<strong>${c.title}</strong> — ${band}, ${score}/100<br/>` +
        `<span style="color:var(--color-text-muted)">Confidence: ${conf}</span><br/>` +
        `<span style="color:var(--color-text-muted)">${indicators}</span>` +
        `</div>`
      );
    };

    for (const candidate of routes) {
      const coords = candidate.geometry.coordinates.map(([lat, lon]) => L.latLng(lat, lon));
      const colors = candidate.risk_colors ?? [];
      const lines: L.Polyline[] = [];
      for (let i = 0; i + 1 < coords.length; i += 1) {
        const color = colors[Math.min(colors.length - 1, i)] ?? riskColor(0.1);
        const line = L.polyline([coords[i], coords[i + 1]], {
          color,
          weight: 4,
          opacity: 0.75,
          className: "route-line",
          interactive: true,
        });
        line.bindTooltip(legend(candidate), {
          direction: "top",
          offset: [0, -8],
        });
        line.on("mouseover", () => {
          apiRef.current?.highlightRoute(candidate.id);
          onSegmentHover(candidate.id);
        });
        line.on("mouseout", () => onSegmentHover(null));
        line.on("click", () => {
          onSelectRoute(candidate.id);
          onSegmentHover(candidate.id);
        });
        line.addTo(map);
        lines.push(line);
      }
      routeLinesRef.current.set(candidate.id, lines);
    }

    // apply selection styling
    routeLinesRef.current.forEach((lines, id) => {
      const active = id === selectedRouteId;
      for (const line of lines) {
        line.setStyle({ weight: active ? 6 : 4, opacity: active ? 1 : 0.75 });
        line.getElement()?.classList.toggle("route-selected", active);
      }
    });

    // fit bounds on first render
    if (routes.length > 0 && !window.__mfFitted) {
      const bounds = L.latLngBounds(
        routes.flatMap((r) => r.geometry.coordinates.map(([lat, lon]) => L.latLng(lat, lon))),
      );
      map.fitBounds(bounds, { padding: [70, 70] });
      window.__mfFitted = true;
    }
  }, [routes, selectedRouteId, onSelectRoute, onSegmentHover, apiRef]);

  // --- incidents ---
  useEffect(() => {
    const group = groupsRef.current?.incident;
    if (!group) return;
    group.clearLayers();
    if (!filters.incidents) return;
    for (const incident of incidents) {
      const marker = L.marker([incident.location.lat, incident.location.lon], {
        icon: incidentIcon(incident.severity),
        title: incident.summary,
      });
      marker.bindPopup(
        `<div class="segment-tooltip"><strong>${incident.category.replace(/_/g, " ")}</strong> (${incident.severity})<br/>` +
          `<span>${incident.summary}</span><br/>` +
          `<span style="color:var(--color-text-muted)">${timeAgo(incident.reported_at)} · ${incident.source}</span></div>`,
      );
      group.addLayer(marker);
    }
  }, [incidents, filters.incidents]);

  // --- lighting ---
  useEffect(() => {
    const group = groupsRef.current?.lighting;
    if (!group) return;
    group.clearLayers();
    if (!filters.lighting) return;
    for (const obs of lighting) {
      const state = obs.working === null ? "uncertain" : obs.working ? "working" : "out";
      const marker = L.marker([obs.lat, obs.lon], {
        icon: lightingIcon(state),
      });
      marker.bindTooltip(
        `<div class="segment-tooltip"><strong>${obs.status_label}</strong><br/>` +
          `<span style="color:var(--color-text-muted)">Confidence: ${obs.confidence} · ${obs.source}</span></div>`,
        { direction: "top" },
      );
      group.addLayer(marker);
    }
  }, [lighting, filters.lighting]);

  // --- facilities ---
  useEffect(() => {
    const group = groupsRef.current?.facility;
    if (!group) return;
    group.clearLayers();
    if (!filters.facilities) return;
    for (const f of facilities) {
      const marker = L.marker([f.lat, f.lon], {
        icon: facilityIcon(f.type),
      });
      marker.bindTooltip(
        `<div class="segment-tooltip"><strong>${f.name}</strong><br/>` +
          `<span style="color:var(--color-text-muted)">${f.type.replace(/_/g, " ")} · ${f.distance_m}m away</span></div>`,
        { direction: "top" },
      );
      group.addLayer(marker);
    }
  }, [facilities, filters.facilities]);

  // --- heatmap ---
  useEffect(() => {
    const group = groupsRef.current?.heat;
    if (!group) return;
    group.clearLayers();
    if (!filters.heatmap) return;
    for (const zone of heatZones) {
      const circle = L.circle([zone.lat, zone.lon], {
        radius: 650,
        color: heatColor(zone.level),
        fillColor: heatColor(zone.level),
        fillOpacity: 0.18,
        weight: 1,
      });
      circle.bindTooltip(
        `<div class="segment-tooltip"><strong>${zone.name}</strong><br/>` +
          `<span style="color:var(--color-text-muted)">Based on available reports and evidence</span></div>`,
        { direction: "top" },
      );
      group.addLayer(circle);
    }
  }, [heatZones, filters.heatmap]);

  return (
    <div ref={containerRef} className="map3d-perspective absolute inset-0 z-0">
      {mode === "3d" ? <div className="map3d-sky" aria-hidden /> : null}
    </div>
  );
}
