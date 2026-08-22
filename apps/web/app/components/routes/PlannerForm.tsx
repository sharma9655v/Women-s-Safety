"use client";
import { useState, FormEvent } from "react";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatDuration, formatDistance } from "@/lib/format";
import { MapPin, Shield, Clock, AlertTriangle, CheckCircle, XCircle, Loader2, Map, Navigation, Car, Bike, Footprints } from "lucide-react";

export function PlannerForm({ onResults }: { onResults: (routes: import("@/lib/types").RouteCandidate[]) => void }) {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [mode, setMode] = useState<"walking" | "driving" | "cycling">("walking");
  const [pref, setPref] = useState<"safety" | "balanced" | "time">("safety");
  const [hour, setHour] = useState(new Date().getHours());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null); setLoading(true);
    try {
      const res = await api.routes({
        origin: { lat: 28.6139, lon: 77.209 },
        destination: { lat: 28.65, lon: 77.23 },
        mode,
        safety_preference: pref,
        hour_ist: hour,
      });
      onResults(res);
    } catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setLoading(false); }
  };

  return (
    <Card className="space-y-4">
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2">
          <Input label="Origin" placeholder="e.g., Connaught Place" value={origin} onChange={e => setOrigin(e.target.value)} required />
          <Input label="Destination" placeholder="e.g., Karol Bagh" value={destination} onChange={e => setDestination(e.target.value)} required />
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <label className="flex items-center gap-2 cursor-pointer"><input type="radio" name="mode" value="walking" checked={mode==="walking"} onChange={()=>setMode("walking")} className="accent-primary" /><Footprints size={16} /><span>Walk</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="radio" name="mode" value="cycling" checked={mode==="cycling"} onChange={()=>setMode("cycling")} className="accent-primary" /><Bike size={16} /><span>Cycle</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="radio" name="mode" value="driving" checked={mode==="driving"} onChange={()=>setMode("driving")} className="accent-primary" /><Car size={16} /><span>Drive</span></label>
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <label className="flex items-center gap-2 cursor-pointer"><input type="radio" name="pref" value="safety" checked={pref==="safety"} onChange={()=>setPref("safety")} className="accent-primary" /><Shield size={16} className="text-safe"/><span>Safest</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="radio" name="pref" value="balanced" checked={pref==="balanced"} onChange={()=>setPref("balanced")} className="accent-primary" /><MapPin size={16} className="text-accent"/><span>Balanced</span></label>
          <label className="flex items-center gap-2 cursor-pointer"><input type="radio" name="pref" value="time" checked={pref==="time"} onChange={()=>setPref("time")} className="accent-primary" /><Clock size={16} className="text-warn"/><span>Fastest</span></label>
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          <Input type="number" label="Simulated Hour (IST 0–23)" min={0} max={23} value={hour} onChange={e=>setHour(Number(e.target.value))} />
        </div>
        {error && <div className="text-sm text-danger">{error}</div>}
        <Button type="submit" className="w-full" disabled={loading || !origin || !destination}>
          {loading ? <Loader2 size={18} className="animate-spin" /> : <>Find Routes <Navigation size={18} /></>}
        </Button>
      </form>
    </Card>
  );
}