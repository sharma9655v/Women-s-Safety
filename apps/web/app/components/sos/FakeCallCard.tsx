"use client";
import { useState } from "react";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { timeAgo } from "@/lib/format";
import { Phone, Loader2, PhoneOff, Bell, X, Check } from "lucide-react";

export function FakeCallCard() {
  const { data: active, mutate } = useQuery("fake-call-active", () => api.fakeCall.active(), { revalidateMs: 10_000 });
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ caller_name: "", caller_number: "", scheduled_at: "" });

  const start = async () => {
    if (!form.caller_name) return;
    setLoading(true);
    try {
      await api.fakeCall.start({ caller_name: form.caller_name, caller_number: form.caller_number || undefined, scheduled_at: form.scheduled_at || undefined });
      mutate();
    } finally { setLoading(false); }
  };

  return (
    <Card className="space-y-4">
      <h3 className="font-display font-semibold flex items-center gap-2"><svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-warn"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg> Fake Call</h3>
      <p className="text-sm text-text-mid">Schedule an incoming call to exit awkward or unsafe situations.</p>

      {active?.session && active.session.status !== "DISMISSED" && active.session.status !== "EXPIRED" ? (
        <div className="glass p-4 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2"><svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-warn"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg><span className="font-medium">{active.session.caller_name}</span></div>
            <Badge variant={active.session.status === "TRIGGERED" ? "success" : "info"}> {active.session.status} </Badge>
          </div>
          <p className="text-sm text-text-mid">Scheduled: {timeAgo(active.session.scheduled_at)}</p>
          <div className="flex gap-2">
            {active.session.status !== "TRIGGERED" && <Button size="sm" variant="primary" onClick={() => { /* trigger logic */ }}>Trigger Now <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg></Button>}
            <Button size="sm" variant="danger" onClick={() => { /* dismiss */ }}>Dismiss <PhoneOff width={16} height={16} /></Button>
          </div>
        </div>
      ) : (
        <div className="glass p-4 rounded-xl space-y-4">
          <Input label="Caller Name" placeholder="e.g., Mom, Boss, Emergency" value={form.caller_name} onChange={e => setForm(f => ({ ...f, caller_name: e.target.value }))} required />
          <Input label="Caller Number (optional)" placeholder="+91 9XXXXXXXXX" value={form.caller_number} onChange={e => setForm(f => ({ ...f, caller_number: e.target.value }))} />
          <Input type="datetime-local" label="Schedule For (optional — defaults to now)" value={form.scheduled_at} onChange={e => setForm(f => ({ ...f, scheduled_at: e.target.value }))} />
          <Button className="w-full" disabled={loading || !form.caller_name} onClick={start}>
            {loading ? <svg width={18} height={18} className="animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" strokeOpacity="0.25"/><path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round"/></svg> : <>Schedule Call <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg></>}
          </Button>
        </div>
      )}
    </Card>
  );
}