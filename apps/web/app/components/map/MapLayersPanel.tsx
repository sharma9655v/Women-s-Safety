"use client";
import { useState } from "react";
import { useNightshieldMap } from "./MapCanvas";
import { HeatmapLayer } from "./HeatmapLayer";
import { IncidentMarkers } from "./IncidentMarkers";
import { SafePlaces } from "./SafePlaces";
import { Badge } from "@/components/ui/Badge";
import { MapPin, AlertTriangle, Shield, Layers, Zap } from "lucide-react";

export function MapLayersPanel({
  heatmap,
  incidents = [],
  facilities = [],
}: { heatmap: { zones: { name: string; lat: number; lon: number; level: number }[] } | null; incidents?: import("@/lib/types").Incident[]; facilities?: import("@/lib/types").Facility[] }) {
  const { map, is3D, toggle3D } = useNightshieldMap();
  const [layers, setLayers] = useState({ heatmap: true, incidents: true, safePlaces: true });
  return (
    <div className="glass p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-display font-semibold">Map Layers</h3>
        <Badge variant={is3D ? "success" : "default"} onClick={toggle3D} className="cursor-pointer">{is3D ? "3D View" : "2D View"}</Badge>
      </div>
      <div className="space-y-2">
        {[
          { key: "heatmap", label: "Heatmap", icon: Zap, active: layers.heatmap, count: heatmap?.zones.length ?? 0 },
          { key: "incidents", label: "Incidents", icon: AlertTriangle, active: layers.incidents, count: incidents.length },
          { key: "safePlaces", label: "Safe Places", icon: Shield, active: layers.safePlaces, count: facilities.length },
        ].map(({ key, label, icon: Icon, active, count }) => (
          <label key={key} className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={active} onChange={e => setLayers(l => ({ ...l, [key]: e.target.checked }))} className="size-4 accent-primary" />
            <Icon size={16} className={`shrink-0 ${active ? "text-primary" : "text-text-low"}`} />
            <span className="text-sm text-text-hi">{label}</span>
            <Badge variant="default" className="ml-auto">{count}</Badge>
          </label>
        ))}
      </div>
      {layers.heatmap && heatmap && <HeatmapLayer data={heatmap} />}
      {layers.incidents && <IncidentMarkers incidents={incidents} />}
      {layers.safePlaces && <SafePlaces facilities={facilities} />}
    </div>
  );
}