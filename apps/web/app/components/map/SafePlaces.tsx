"use client";
import { useEffect } from "react";
import { useNightshieldMap } from "./MapCanvas";

export function SafePlaces({ facilities }: { facilities: import("@/lib/types").Facility[] }) {
  const { map, addLayer, removeLayer, addSource, removeSource } = useNightshieldMap();
  useEffect(() => {
    if (!map.current || !map.current.loaded()) return;
    const sourceId = "safe-places";
    const layerId = "safe-places-layer";
    const features = facilities.map(f => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [f.lon, f.lat] },
      properties: { id: f.id, type: f.type, name: f.name },
    }));
    addSource(sourceId, { type: "geojson", data: { type: "FeatureCollection", features }, cluster: false });
    addLayer({
      id: layerId, type: "symbol", source: sourceId,
      layout: { "icon-image": ["get", "type"], "icon-size": 0.7, "icon-allow-overlap": true },
      paint: { "icon-opacity": 0.9 },
    });
    return () => { removeLayer(layerId); removeSource(sourceId); };
  }, [facilities, map, addLayer, removeLayer, addSource, removeSource]);
  return null;
}