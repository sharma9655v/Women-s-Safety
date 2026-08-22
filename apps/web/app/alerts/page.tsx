"use client";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { formatDistance, timeAgo, freshnessFromAge, FRESHNESS_STYLE } from "@/lib/format";
import { AlertTriangle, MapPin, Loader2, Plus, Search, Filter, Bell, AlertCircle, CheckCircle, Clock, MapPin as MapPinIcon } from "lucide-react";
import { useState } from "react";

export default function AlertsPage() {
  const [filter, setFilter] = useState("");
  const { data: alerts, mutate } = useQuery("alerts-page", () => api.activeAlerts(), { revalidateMs: 30_000 });
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ category: "recent_verified_incident", severity: "moderate" as "high" | "moderate" | "low" | "critical" | undefined, lat: 28.6139, lon: 77.209, location_name: "", description: "" });

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.alerts.create({ ...form, lat: Number(form.lat), lon: Number(form.lon) });
      setShowCreate(false);
      mutate();
    } catch (err) { alert("Failed to create alert"); }
  };

  const filtered = alerts?.alerts?.filter(a => a.category.toLowerCase().includes(filter.toLowerCase()) || a.location_name?.toLowerCase().includes(filter.toLowerCase())) ?? [];

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      <div className="p-4 sm:p-6 border-b border-line">
        <div className="mx-auto max-w-4xl flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-bold">Alerts & Incidents</h1>
            <p className="text-sm text-text-mid">Verified community safety alerts. Create new alerts to warn others.</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowCreate(!showCreate)}><Plus size={16} /> Create Alert</Button>
            <Button size="sm" onClick={() => mutate()}><Loader2 size={16} className="animate-spin" /></Button>
          </div>
        </div>
        {showCreate && (
          <form onSubmit={create} className="mx-auto max-w-4xl p-4 border-t border-line glass animate-in space-y-3">
            <h3 className="font-medium">New Community Alert</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <select className="px-4 py-2.5 bg-surface-elevated/50 border border-line rounded-xl text-text-hi focus:outline-none focus:ring-2 focus:ring-primary/40" value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}>
                <option value="recent_verified_incident">Recent Verified Incident</option>
                <option value="lighting_issue">Lighting Issue</option>
                <option value="road_hazard">Road Hazard</option>
                <option value="blocked_sidewalk">Blocked Sidewalk</option>
                <option value="route_obstruction">Route Obstruction</option>
                <option value="weather_hazard">Weather Hazard</option>
                <option value="emergency_event">Emergency Event</option>
                <option value="public_safety_notice">Public Safety Notice</option>
              </select>
              <select className="px-4 py-2.5 bg-surface-elevated/50 border border-line rounded-xl text-text-hi focus:outline-none focus:ring-2 focus:ring-primary/40" value={form.severity} onChange={e => setForm(f => ({ ...f, severity: e.target.value as "high" | "moderate" | "low" | "critical" | undefined }))}>
                <option value="low">Low</option>
                <option value="moderate">Moderate</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Input label="Latitude" type="number" step="any" value={form.lat} onChange={e => setForm(f => ({ ...f, lat: Number(e.target.value) }))} />
              <Input label="Longitude" type="number" step="any" value={form.lon} onChange={e => setForm(f => ({ ...f, lon: Number(e.target.value) }))} />
            </div>
            <Input label="Location Name" placeholder="e.g., Near Metro Station" value={form.location_name} onChange={e => setForm(f => ({ ...f, location_name: e.target.value }))} />
            <Input label="Description (optional)" placeholder="Brief details" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            <div className="flex gap-2 pt-2">
              <Button type="submit">Submit Alert <AlertTriangle size={16} /></Button>
              <Button type="button" variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            </div>
          </form>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="mx-auto max-w-4xl space-y-4">
          <div className="flex gap-2">
            <div className="flex-1 relative"><Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-low" /><Input placeholder="Filter alerts…" value={filter} onChange={e => setFilter(e.target.value)} className="pl-10" /></div>
          </div>

          {filtered.length === 0 ? (
            <Card variant="glass" className="text-center py-12"><AlertCircle size={48} className="mx-auto text-text-low mb-4" /><p className="text-text-mid">No alerts match your filter</p></Card>
          ) : (
            <div className="space-y-3">
              {filtered.map(a => {
                const freshness = freshnessFromAge(a.expires_at ? (new Date(a.expires_at).getTime() - Date.now()) / 3600_000 : null);
                return (
                  <Card key={a.id} variant="glass" className="border-l-4 border-warn">
                    <div className="flex items-start gap-3">
                      <div className="size-10 rounded-xl bg-warn/20 flex items-center justify-center shrink-0"><AlertTriangle size={20} className="text-warn" /></div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge variant={a.severity === "critical" ? "danger" : a.severity === "high" ? "danger" : a.severity === "moderate" ? "warn" : "info"}>{a.severity}</Badge>
                          <Badge variant="default">{a.category}</Badge>
                          <Badge className={FRESHNESS_STYLE[freshness.tier]}>{freshness.label}</Badge>
                        </div>
                        <p className="font-medium truncate mt-1">{a.location_name ?? `Lat: ${a.lat.toFixed(4)}, Lon: ${a.lon.toFixed(4)}`}</p>
                        {a.description && <p className="text-sm text-text-mid mt-1 line-clamp-2">{a.description}</p>}
                        <div className="flex items-center gap-3 mt-2 text-xs text-text-low">
                          <span className="flex items-center gap-1"><MapPinIcon size={12} /> {a.lat.toFixed(4)}, {a.lon.toFixed(4)}</span>
                          <span className="flex items-center gap-1"><Clock size={12} /> {timeAgo(a.observed_at)}</span>
                          <span className="flex items-center gap-1"><Bell size={12} /> {a.source}</span>
                        </div>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}