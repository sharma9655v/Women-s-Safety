"use client";
import { useState } from "react";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { formatDuration, timeAgo } from "@/lib/format";
import { MapPin, Clock, AlertTriangle, CheckCircle, XCircle, Loader2, Flag, UserPlus } from "lucide-react";

export function JourneyCheckin() {
  const { data: active, mutate } = useQuery("journey-active", () => api.journey.active(), { revalidateMs: 10_000 });
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ destination_name: "", destination_lat: null as number | null, destination_lon: null as number | null, expected_arrival_at: "", checkin_interval_s: 900, checkin_grace_s: 300, contact_ids: [] as number[] });

  const start = async () => {
    if (!form.destination_name || form.destination_lat === null || form.destination_lon === null || form.contact_ids.length === 0) return;
    setLoading(true);
    try {
      await api.journey.start({ ...form, expected_arrival_at: form.expected_arrival_at || undefined });
      mutate();
    } finally { setLoading(false); }
  };

  return (
    <Card className="space-y-4">
      <h3 className="font-display font-semibold flex items-center gap-2"><Flag size={22} className="text-accent" /> Journey Check-in</h3>
      <p className="text-sm text-text-mid">Set a destination and check-in interval. Miss a check-in and your contacts are alerted.</p>

      {active && active.length > 0 ? (
        <div className="space-y-3">
          {active.map(s => (
            <div key={s.session_id} className="glass p-4 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2"><Flag size={20} className="text-accent" /><span className="font-medium">{s.destination_name}</span></div>
                <Badge variant={s.status === "ACTIVE" ? "success" : "warn"}> {s.status} </Badge>
              </div>
              <div className="grid gap-2 sm:grid-cols-2 text-sm">
                <div className="glass p-2 rounded-lg"><MapPin size={14} className="text-accent" /><span className="ml-2">Next: {s.next_checkin_at ? timeAgo(s.next_checkin_at) : "—"}</span></div>
                <div className="glass p-2 rounded-lg"><Clock size={14} className="text-accent" /><span className="ml-2">Interval: {formatDuration(s.checkin_interval_s)}</span></div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => api.journey.checkin(s.session_id)}><CheckCircle size={16} /> Check In</Button>
                <Button size="sm" variant="danger" onClick={() => api.journey.end(s.session_id, "user_cancelled")}><XCircle size={16} /> End</Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="glass p-4 rounded-xl space-y-4">
          <Input label="Destination Name" placeholder="e.g., Home, Office" value={form.destination_name} onChange={e => setForm(f => ({ ...f, destination_name: e.target.value }))} required />
          <div className="grid gap-2 sm:grid-cols-2">
            <Input type="number" step="any" label="Dest Latitude" placeholder="28.6139" value={form.destination_lat ?? ""} onChange={e => setForm(f => ({ ...f, destination_lat: Number(e.target.value) }))} />
            <Input type="number" step="any" label="Dest Longitude" placeholder="77.2090" value={form.destination_lon ?? ""} onChange={e => setForm(f => ({ ...f, destination_lon: Number(e.target.value) }))} />
          </div>
          <div className="grid gap-2 sm:grid-cols-3">
            <Input type="datetime-local" label="Expected Arrival (optional)" value={form.expected_arrival_at} onChange={e => setForm(f => ({ ...f, expected_arrival_at: e.target.value }))} />
            <Input type="number" label="Check-in Interval (s)" min={60} value={form.checkin_interval_s} onChange={e => setForm(f => ({ ...f, checkin_interval_s: Number(e.target.value) }))} />
            <Input type="number" label="Grace Period (s)" min={30} value={form.checkin_grace_s} onChange={e => setForm(f => ({ ...f, checkin_grace_s: Number(e.target.value) }))} />
          </div>
          <div className="flex flex-wrap gap-2">
            <label className="cursor-pointer"><input type="checkbox" className="accent-primary" /> Use current location as destination</label>
          </div>
          <Button className="w-full" disabled={loading || !form.destination_name || form.destination_lat === null || form.destination_lon === null || form.contact_ids.length === 0} onClick={start}>
            {loading ? <svg width={18} height={18} className="animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" strokeOpacity="0.25"/><path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round"/></svg> : <>Start Journey <Flag size={18} /></>}
          </Button>
        </div>
      )}
    </Card>
  );
}