"use client";
import { useEffect } from "react";
import { useNightshieldMap } from "./MapCanvas";

export function HeatmapLayer({ data }: { data: { zones: { name: string; lat: number; lon: number; level: number }[] } }) {
  const { map, addLayer, removeLayer, addSource, removeSource } = useNightshieldMap();
  useEffect(() => {
    if (!map.current || !map.current.loaded()) return;
    const sourceId = "heatmap";
    const layerId = "heatmap-layer";
    const features = data.zones.map(z => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [z.lon, z.lat] },
      properties: { level: z.level, name: z.name },
    }));
    addSource(sourceId, { type: "geojson", data: { type: "FeatureCollection", features }, cluster: false });
    addLayer({
      id: layerId, type: "circle", source: sourceId,
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["get", "level"], 0, 8, 0.5, 24, 1, 48],
        "circle-color": ["interpolate", ["linear"], ["get", "level"], 0, "#3ddc97", 0.3, "#ffb454", 0.6, "#ff8a5c", 1, "#ff5d73"],
        "circle-opacity": 0.6, "circle-blur": 0.5,
      },
    });
    return () => { removeLayer(layerId); removeSource(sourceId); };
  }, [data, map, addLayer, removeLayer, addSource, removeSource]);
  return null;
}