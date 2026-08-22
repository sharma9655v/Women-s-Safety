"use client";
import * as maplibregl from "maplibre-gl";
import type { Map as MLMap, LngLatLike } from "maplibre-gl";
import { useEffect, useRef, useState, useCallback } from "react";

const STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
const DEFAULT_CENTER: LngLatLike = [77.209, 28.6139];
const DEFAULT_ZOOM = 11;

export function useNightshieldMap() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const [is3D, set3D] = useState(false);
  const [mapLoaded, setMapLoaded] = useState(false);

  useEffect(() => {
    const map = new maplibregl.Map({
      container: containerRef.current!,
      style: STYLE,
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      pitch: 0,
      bearing: -14,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");
    map.on("load", () => setMapLoaded(true));
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; setMapLoaded(false); };
  }, []);

  const setCenter = useCallback((center: LngLatLike, zoom?: number) => {
    mapRef.current?.flyTo({ center, zoom: zoom ?? mapRef.current?.getZoom(), duration: 1000, essential: true });
  }, []);

  const toggle3D = useCallback(() => set3D(p => {
    const next = !p;
    const m = mapRef.current!;
    m.easeTo({ pitch: next ? 58 : 0, bearing: next ? -28 : -14, duration: 900, essential: true });
    return next;
  }), []);

  const addLayer = useCallback((layer: any, before?: string) => {
    if (!mapRef.current) return;
    if (mapRef.current.getLayer(layer.id)) mapRef.current.removeLayer(layer.id);
    mapRef.current.addLayer(layer, before);
  }, []);

  const removeLayer = useCallback((id: string) => { mapRef.current?.getLayer(id) && mapRef.current.removeLayer(id); }, []);

  const addSource = useCallback((id: string, source: any) => {
    if (!mapRef.current) return;
    if (mapRef.current.getSource(id)) mapRef.current.removeSource(id);
    mapRef.current.addSource(id, source);
  }, []);

  const removeSource = useCallback((id: string) => { mapRef.current?.getSource(id) && mapRef.current.removeSource(id); }, []);

  return { ref: containerRef, map: mapRef, is3D, toggle3D, mapLoaded, setCenter, addLayer, removeLayer, addSource, removeSource };
}

export function MapCanvas({ className = "" }: { className?: string }) {
  const { ref, is3D, toggle3D, mapLoaded } = useNightshieldMap();
  return (
    <div ref={ref} className={`relative h-full w-full rounded-2xl overflow-hidden ${className}`}>
      {!mapLoaded && <div className="absolute inset-0 flex items-center justify-center bg-bg/50 text-text-low">Loading map…</div>}
      <div className="absolute bottom-3 right-3 z-10 flex gap-2">
        <button onClick={toggle3D} className={`px-3 py-1.5 rounded-xl text-sm font-medium transition-colors ${is3D ? "bg-primary text-bg shadow-primary-glow" : "bg-surface-elevated text-text-hi hover:bg-white/5"}`} aria-pressed={is3D}>
          {is3D ? "2D" : "3D"}
        </button>
      </div>
    </div>
  );
}