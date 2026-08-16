"use client";

import { Check, ChevronUp } from "lucide-react";
import { useState } from "react";

interface MapLayer {
  id: string;
  label: string;
  color: string;
  defaultChecked: boolean;
}

const LAYERS: MapLayer[] = [
  { id: "incidents", label: "Incidents", color: "var(--emergency)", defaultChecked: true },
  { id: "alerts", label: "Alerts", color: "var(--warning)", defaultChecked: true },
  { id: "lighting", label: "Lighting", color: "var(--success)", defaultChecked: true },
  { id: "facilities", label: "Facilities", color: "var(--info)", defaultChecked: true },
  { id: "heatmap", label: "Heatmap", color: "var(--primary)", defaultChecked: true },
];

export interface MapLayerFilters {
  incidents: boolean;
  alerts: boolean;
  lighting: boolean;
  facilities: boolean;
  heatmap: boolean;
}

export function MapLayersPanel({
  filters,
  onChange,
}: {
  filters: MapLayerFilters;
  onChange: (filters: MapLayerFilters) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);

  const toggle = (id: string) => {
    onChange({ ...filters, [id]: !filters[id as keyof MapLayerFilters] });
  };

  return (
    <div className="map-layers-panel">
      <div className="map-layers-title">
        <span>Map Layers</span>
        <button
          type="button"
          onClick={() => setCollapsed(!collapsed)}
          className="flex size-5 items-center justify-center rounded text-text-muted transition-colors hover:text-foreground"
          aria-label={collapsed ? "Expand layers" : "Collapse layers"}
        >
          <ChevronUp
            className={`size-3.5 transition-transform duration-200 ${collapsed ? "rotate-180" : ""}`}
            aria-hidden
          />
        </button>
      </div>
      {!collapsed &&
        LAYERS.map((layer) => {
          const checked = filters[layer.id as keyof MapLayerFilters];
          return (
            <button
              key={layer.id}
              type="button"
              className="map-layer-item"
              onClick={() => toggle(layer.id)}
              aria-pressed={checked}
            >
              <span className={`map-layer-checkbox ${checked ? "is-checked" : ""}`}>
                {checked && <Check className="size-2.5 text-white" aria-hidden />}
              </span>
              <span className="map-layer-dot" style={{ background: layer.color }} aria-hidden />
              <span>{layer.label}</span>
            </button>
          );
        })}
    </div>
  );
}
