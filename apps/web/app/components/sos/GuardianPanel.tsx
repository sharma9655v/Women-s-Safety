"use client";
import { useState } from "react";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { formatDuration, timeAgo } from "@/lib/format";
import { Shield, Clock, MapPin, AlertTriangle, CheckCircle, XCircle, Loader2, X, Check, RefreshCw, UserPlus } from "lucide-react";
import { formatDistance } from "@/lib/format";

export function GuardianPanel() {
  const { data: active, mutate } = useQuery("guardian-active", () => api.guardian.active(), { revalidateMs: 10_000 });
  const [loading, setLoading] = useState(false);
  const [contactIds, setContactIds] = useState<number[]>([]);

  const start = async () => {
    if (contactIds.length === 0) return;
    setLoading(true);
    try {
      await api.guardian.start({ guardian_contact_ids: contactIds });
      mutate();
    } finally { setLoading(false); }
  };

  return (
    <Card className="space-y-4">
      <h3 className="font-display font-semibold flex items-center gap-2"><Shield size={22} className="text-primary" /> Guardian Mode</h3>
      <p className="text-sm text-text-mid">Share your journey with trusted contacts. They'll be notified if you miss a check-in.</p>

      {active && active.length > 0 ? (
        <div className="space-y-3">
          {active.map(s => (
            <div key={s.session_id} className="glass p-4 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2"><Shield size={20} className="text-safe" /><span className="font-medium">Active Guardian</span></div>
                <Badge variant="success">ACTIVE</Badge>
              </div>
              <div className="grid gap-2 sm:grid-cols-2 text-sm">
                <div className="glass p-2 rounded-lg"><Clock size={14} className="text-accent" /><span className="ml-2">Deadline: {s.checkin_deadline ? timeAgo(s.checkin_deadline) : "—"}</span></div>
                <div className="glass p-2 rounded-lg"><MapPin size={14} className="text-accent" /><span className="ml-2">Last: {s.last_known_at ? timeAgo(s.last_known_at) : "—"}</span></div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => api.guardian.checkin(s.session_id)}><CheckCircle size={16} /> Check In Now</Button>
                <Button size="sm" variant="danger" onClick={() => api.guardian.end(s.session_id, "user_cancelled")}><XCircle size={16} /> End</Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="glass p-4 rounded-xl space-y-3">
          <label className="block text-sm text-text-mid">Select contacts to notify</label>
          <div className="flex flex-wrap gap-2">
            <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" className="accent-primary" /><span className="text-sm">Contact 1</span></label>
            <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" className="accent-primary" /><span className="text-sm">Contact 2</span></label>
          </div>
          <Button className="w-full" disabled={loading || contactIds.length === 0} onClick={start}>
            {loading ? <svg width={18} height={18} className="animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" strokeOpacity="0.25"/><path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round"/></svg> : <>Start Guardian <Shield size={18} /></>}
          </Button>
        </div>
      )}
    </Card>
  );
}