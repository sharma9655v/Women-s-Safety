"use client";
import { useEffect } from "react";
import { useNightshieldMap } from "./MapCanvas";

export function IncidentMarkers({ incidents }: { incidents: import("@/lib/types").Incident[] }) {
  const { map, addLayer, removeLayer, addSource, removeSource } = useNightshieldMap();
  useEffect(() => {
    if (!map.current || !map.current.loaded()) return;
    const sourceId = "incidents";
    const layerId = "incidents-layer";
    const features = incidents.map(i => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [i.location.lon, i.location.lat] },
      properties: { id: i.id, severity: i.severity, category: i.category, summary: i.summary },
    }));
    addSource(sourceId, { type: "geojson", data: { type: "FeatureCollection", features } });
    addLayer({
      id: layerId, type: "circle", source: sourceId,
      paint: {
        "circle-radius": 8, "circle-stroke-width": 2,
        "circle-color": ["match", ["get", "severity"], "critical", "#e11d48", "high", "#ff5d73", "moderate", "#ffb454", "#3ddc97"],
        "circle-stroke-color": "#fff", "circle-opacity": 0.9,
      },
    });
    return () => { removeLayer(layerId); removeSource(sourceId); };
  }, [incidents, map, addLayer, removeLayer, addSource, removeSource]);
  return null;
}