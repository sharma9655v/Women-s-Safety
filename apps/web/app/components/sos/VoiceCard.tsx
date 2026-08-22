"use client";
import { useState } from "react";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Mic, MicOff, Loader2, Volume2, X, Check } from "lucide-react";

export function VoiceCard() {
  const { data: status, mutate } = useQuery("voice-status", () => api.voice.status(""), { revalidateMs: 5_000, retry: 0 });
  const [loading, setLoading] = useState(false);

  const start = async () => {
    setLoading(true);
    try {
      await api.voice.start({ route_session_id: "current", language: "en" });
      mutate();
    } finally { setLoading(false); }
  };
  const stop = async () => {
    setLoading(true);
    try {
      await api.voice.stop("");
      mutate();
    } finally { setLoading(false); }
  };

  return (
    <Card className="space-y-4">
      <h3 className="font-display font-semibold flex items-center gap-2"><Mic size={22} className="text-info" /> Voice Guidance</h3>
      <p className="text-sm text-text-mid">Turn-by-turn voice navigation for your active route.</p>

      {status?.active ? (
        <div className="glass p-4 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2"><Mic size={20} className="text-info" /><span className="font-medium">Voice Active</span></div>
            <Badge variant="success">LIVE</Badge>
          </div>
          <p className="text-sm text-text-mid">Language: {status.language}</p>
          <Button variant="danger" className="w-full" onClick={stop} disabled={loading}><svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 9v3m3-3h3M9 12l6-6M9 12l-6 6M12 12l6 6M12 12l-6-6"/></svg> Stop Voice</Button>
        </div>
      ) : (
        <div className="glass p-4 rounded-xl space-y-3">
          <label className="block text-sm text-text-mid">Language</label>
          <select className="w-full px-4 py-2.5 bg-surface-elevated/50 border border-line rounded-xl text-text-hi focus:outline-none focus:ring-2 focus:ring-primary/40" defaultValue="en">
            <option value="en">English</option>
            <option value="hi">Hindi</option>
            <option value="mr">Marathi</option>
          </select>
          <Button className="w-full" onClick={start} disabled={loading}><svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/></svg> {loading ? <svg width={18} height={18} className="animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" strokeOpacity="0.25"/><path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round"/></svg> : "Start Voice Guidance"}</Button>
        </div>
      )}
    </Card>
  );
}