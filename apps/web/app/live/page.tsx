"use client";
export const dynamic = "force-dynamic";
import { useState } from "react";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { MapCanvas, useNightshieldMap } from "@/components/map/MapCanvas";
import { MapLayersPanel } from "@/components/map/MapLayersPanel";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Tabs } from "@/components/ui/Tabs";
import { formatDuration, formatDistance, riskBandLabel, riskBandStyle, FRESHNESS_STYLE, freshnessFromAge } from "@/lib/format";
import { Loader2, MapPin, AlertTriangle, Shield, Users, Layers, Zap, RefreshCw, Target, Map, Pin } from "lucide-react";

export default function LiveDashboard() {
  const [selectedSegment, setSelectedSegment] = useState<number | null>(null);
  const { data: heatmap, mutate: mutateHeatmap } = useQuery("heatmap-live", () => api.heatmap("77.0,28.5,77.4,28.8", 11), { revalidateMs: 30_000 });
  const { data: incidents } = useQuery("incidents-live", () => api.incidents(), { revalidateMs: 30_000 });
  const { data: facilities } = useQuery("facilities-live", () => api.facilities(), { revalidateMs: 60_000 });
  const { data: areas } = useQuery("areas-live", () => api.areas(), { revalidateMs: 60_000 });
  const { data: alerts } = useQuery("alerts-live", () => api.activeAlerts(), { revalidateMs: 30_000 });
  const { mapLoaded, is3D, toggle3D } = useNightshieldMap();

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col lg:flex-row">
      {/* Map */}
      <div className="lg:w-2/3 h-full lg:h-[calc(100vh-4rem)] relative">
        <MapCanvas className="h-full" />
        {!mapLoaded && <div className="absolute inset-0 flex items-center justify-center bg-bg/80 z-10"><Loader2 size={32} className="animate-spin text-primary" /></div>}
        <MapLayersPanel heatmap={heatmap ?? { zones: [] }} incidents={incidents} facilities={facilities} />
      </div>

      {/* Right panel */}
      <aside className="lg:w-1/3 h-[calc(100vh-4rem)] overflow-y-auto border-l border-line flex flex-col">
        <div className="p-4 border-b border-line flex items-center justify-between sticky top-0 bg-surface/95 backdrop-blur z-10">
          <h2 className="font-display font-semibold">Live Dashboard</h2>
          <div className="flex items-center gap-2">
            <Badge variant={is3D ? "success" : "default"} onClick={toggle3D} className="cursor-pointer">{is3D ? "3D" : "2D"}</Badge>
            <Button variant="ghost" size="icon" onClick={() => { mutateHeatmap(); }} aria-label="Refresh"><RefreshCw size={18} /></Button>
          </div>
        </div>

        <Tabs defaultValue="alerts" items={[
          { value: "alerts", label: "Alerts" },
          { value: "areas", label: "Areas" },
          { value: "incidents", label: "Incidents" },
          { value: "facilities", label: "Safe Places" },
        ]}>
          {(tab) => (
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {tab === "alerts" && (
                <div className="space-y-3">
                  <h3 className="font-medium flex items-center gap-2"><AlertTriangle size={18} className="text-warn" /> Active Alerts</h3>
                  {alerts?.alerts?.length === 0 ? <p className="text-text-low text-sm">No active alerts</p> : (
                    alerts?.alerts?.slice(0, 10).map(a => (
                      <div key={a.id} className="glass p-3 rounded-xl border-l-4 border-warn">
                        <div className="flex items-start gap-2">
                          <MapPin size={16} className="text-warn shrink-0 mt-0.5" />
                          <div className="flex-1 min-w-0">
                            <p className="font-medium truncate">{a.location_name ?? `Lat: ${a.lat.toFixed(4)}, Lon: ${a.lon.toFixed(4)}`}</p>
                            <p className="text-xs text-text-mid">{a.category} • {a.severity}</p>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {tab === "areas" && (
                <div className="space-y-3">
                  <h3 className="font-medium flex items-center gap-2"><Target size={18} className="text-accent" /> Area Safety Scores</h3>
                  {areas?.map(a => {
                    const bandStyle = riskBandStyle(a.score.band);
                    return (
                      <div key={a.area_name} className="glass p-3 rounded-xl">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{a.area_name}</span>
                          <Badge className={bandStyle}>{riskBandLabel(a.score.band)}</Badge>
                        </div>
                        <div className="mt-2 flex items-center gap-2 text-xs text-text-mid">
                          <span>Incidents: {a.recent_incidents}</span>
                          <span>Lighting: {a.lighting_summary}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {tab === "incidents" && (
                <div className="space-y-3">
                  <h3 className="font-medium flex items-center gap-2"><MapPin size={18} className="text-danger" /> Recent Incidents</h3>
                  {incidents?.slice(0, 10).map(i => (
                    <div key={i.id} className="glass p-3 rounded-xl">
                      <div className="flex items-start gap-2">
                        <MapPin size={16} className="text-danger shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{i.location.name}</p>
                          <p className="text-xs text-text-mid">{i.category} • {i.severity} • {i.verified ? "Verified" : "Unverified"}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {tab === "facilities" && (
                <div className="space-y-3">
                  <h3 className="font-medium flex items-center gap-2"><Shield size={18} className="text-safe" /> Safe Places</h3>
                  {facilities?.slice(0, 10).map(f => (
                    <div key={f.id} className="glass p-3 rounded-xl">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Pin size={16} className="text-safe" />
                          <span className="font-medium">{f.name}</span>
                        </div>
                        <Badge variant="default">{f.type}</Badge>
                      </div>
                      <p className="text-xs text-text-mid mt-1">{f.distance_m ? formatDistance(f.distance_m) : "Distance unknown"}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </Tabs>
      </aside>
    </div>
  );
}