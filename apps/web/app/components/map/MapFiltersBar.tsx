"use client";

import { AlertTriangle, Bell, Building2, Flame, Lightbulb } from "lucide-react";
import type { MapFilters } from "./MapCanvas";

const FILTERS: {
  key: keyof MapFilters;
  label: string;
  icon: typeof AlertTriangle;
}[] = [
  { key: "incidents", label: "Incidents", icon: AlertTriangle },
  { key: "alerts", label: "Alerts", icon: Bell },
  { key: "lighting", label: "Lighting", icon: Lightbulb },
  { key: "facilities", label: "Facilities", icon: Building2 },
  { key: "heatmap", label: "Heatmap", icon: Flame },
];

export function MapFiltersBar({
  filters,
  onChange,
}: {
  filters: MapFilters;
  onChange: (f: MapFilters) => void;
}) {
  return (
    <div className="flex gap-1">
      {FILTERS.map((f) => {
        const active = filters[f.key];
        const Icon = f.icon;
        return (
          <button
            key={f.key}
            type="button"
            onClick={() => onChange({ ...filters, [f.key]: !active })}
            title={f.label}
            aria-pressed={active}
            className={`map-filter-button flex min-h-11 min-w-11 cursor-pointer items-center justify-center gap-1 rounded-lg border px-2 py-1.5 text-[11px] font-medium backdrop-blur-md transition-all duration-200 select-none ${
              active
                ? "border-primary/30 bg-primary/12 text-primary shadow-sm"
                : "border-border bg-surface/80 text-text-muted hover:bg-surface-hover hover:text-text-secondary"
            }`}
          >
            <Icon className="size-3.5" aria-hidden />
            <span className="hidden sm:inline">{f.label}</span>
          </button>
        );
      })}
    </div>
  );
}
