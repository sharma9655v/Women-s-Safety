"use client";

import { Eye } from "lucide-react";
import { Card, CardHeader } from "@/app/components/ui/Card";
import { Progress } from "@/app/components/ui/Progress";

export interface HeatZone {
  name: string;
  lat: number;
  lon: number;
  level: number;
}

export function SafetyHeatmapPanel({
  zones,
  onFocusZone,
}: {
  zones: HeatZone[];
  onFocusZone?: () => void;
}) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader
        title="Area Risk Map"
        subtitle="Based on aggregated evidence"
        action={
          onFocusZone ? (
            <button
              type="button"
              onClick={onFocusZone}
              className="flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-primary transition-colors hover:bg-primary/8"
            >
              <Eye className="size-3" aria-hidden /> View
            </button>
          ) : undefined
        }
      />
      {zones.length === 0 ? (
        <p className="py-6 text-center text-xs text-text-muted">No heatmap data available.</p>
      ) : (
        <div className="flex-1 space-y-3 overflow-y-auto">
          {zones.map((zone) => {
            const tone: "success" | "warning" | "danger" =
              zone.level < 0.35 ? "success" : zone.level < 0.5 ? "warning" : "danger";
            return (
              <div key={zone.name} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-foreground">{zone.name}</span>
                  <span className="text-text-muted">{Math.round(zone.level * 100)}%</span>
                </div>
                <Progress value={Math.round(zone.level * 100)} tone={tone} />
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
