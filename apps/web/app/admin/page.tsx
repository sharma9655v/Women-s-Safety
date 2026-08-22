"use client";
import { useState } from "react";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Shield, Loader2, RefreshCw, CheckCircle, XCircle, AlertTriangle, Database, Cpu, Key, Eye, Search } from "lucide-react";

export default function AdminPage() {
  const [adminKey, setAdminKey] = useState("");
  const [keyValid, setKeyValid] = useState(false);
  const [reports, setReports] = useState<import("@/lib/types").AdminReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedReport, setSelectedReport] = useState<import("@/lib/types").AdminReport | null>(null);

  const verifyKey = async () => {
    // In real app, this would call an auth endpoint. For demo, accept "dev-admin-key"
    setKeyValid(adminKey === "dev-admin-key" || adminKey.length > 10);
    if (keyValid) loadReports();
  };

  const loadReports = async () => {
    setLoading(true);
    try { const res = await api.admin.reports(adminKey); setReports(res.reports); } catch { alert("Failed to load reports"); }
    finally { setLoading(false); }
  };

  const moderate = async (reportId: number, state: "VERIFIED" | "REJECTED") => {
    // Admin endpoint - would need proper implementation
    setReports(r => r.map(x => x.report_id === reportId ? { ...x, verification_state: state } : x));
  };

  const recompute = async () => {
    setLoading(true);
    try { await api.admin.recompute(adminKey); } catch { alert("Recompute failed"); } finally { setLoading(false); }
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      <div className="p-4 sm:p-6 border-b border-line bg-emergency/5">
        <div className="mx-auto max-w-4xl">
          <div className="flex items-center gap-3 mb-2">
            <div className="size-10 rounded-xl bg-emergency/20 flex items-center justify-center"><Shield size={22} className="text-emergency" /></div>
            <div>
              <h1 className="font-display text-2xl font-bold text-emergency">Admin Console</h1>
              <p className="text-sm text-text-mid">Verify reports, trigger recompute, manage models.</p>
            </div>
          </div>
          {!keyValid ? (
            <div className="glass p-4 rounded-xl space-y-3">
              <Input label="Admin Key" type="password" placeholder="Enter admin key" value={adminKey} onChange={e => setAdminKey(e.target.value)} />
              <Button className="w-full" onClick={verifyKey} disabled={!adminKey}><Key size={16} /> Unlock</Button>
              <p className="text-xs text-text-mid text-center">Demo key: <code className="font-mono bg-surface-elevated px-1 rounded">dev-admin-key</code></p>
            </div>
          ) : (
            <div className="flex gap-2">
              <Button variant="outline" onClick={loadReports} disabled={loading}><RefreshCw size={16} /> Refresh</Button>
              <Button variant="outline" onClick={recompute} disabled={loading}><Cpu size={16} /> Recompute All</Button>
              <Button variant="danger" onClick={() => setKeyValid(false)}><Eye size={16} /> Lock Console</Button>
            </div>
          )}
        </div>
      </div>

      {keyValid && (
        <div className="flex-1 overflow-y-auto p-4">
          <div className="mx-auto max-w-4xl space-y-6">
            {/* Reports */}
            <Card variant="glass">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-medium flex items-center gap-2"><Database size={20} className="text-primary" /> Pending Reports ({reports.length})</h3>
                <div className="flex gap-2"><Input placeholder="Filter…" className="w-64" /><Button variant="outline" size="sm" onClick={loadReports} disabled={loading}><RefreshCw size={16} /></Button></div>
              </div>
              {loading ? (
                <div className="text-center py-8"><Loader2 size={32} className="mx-auto animate-spin text-primary" /></div>
              ) : reports.length === 0 ? (
                <div className="text-center py-8 text-text-mid">No pending reports</div>
              ) : (
                <div className="space-y-3 max-h-[500px] overflow-y-auto">
                  {reports.map(r => (
                    <div key={r.report_id} className="glass p-4 rounded-xl border-l-4 border-warn">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge variant={r.verification_state === "VERIFIED" ? "success" : r.verification_state === "REJECTED" ? "danger" : "warn"}> {r.verification_state} </Badge>
                            <Badge variant="default">Seg #{r.segment_id}</Badge>
                            <Badge variant="info">Conf: {(r.confidence * 100).toFixed(0)}%</Badge>
                          </div>
                          <p className="text-sm text-text-mid mt-1">{r.category}</p>
                          <p className="text-xs text-text-low mt-1">Reported: {new Date(r.reported_at).toLocaleString()}</p>
                        </div>
                        <div className="flex gap-1">
                          <Button size="sm" variant="success" onClick={() => moderate(r.report_id, "VERIFIED")} disabled={r.verification_state !== "PENDING"}><CheckCircle size={14} /> Verify</Button>
                          <Button size="sm" variant="danger" onClick={() => moderate(r.report_id, "REJECTED")} disabled={r.verification_state !== "PENDING"}><XCircle size={14} /> Reject</Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Model Admin */}
            <Card variant="glass">
              <h3 className="font-medium flex items-center gap-2 mb-4"><Cpu size={20} className="text-accent" /> Model Management</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <Card variant="glass-strong" className="p-4">
                  <div className="flex items-center gap-3"><Cpu size={24} className="text-accent" /><div><p className="font-medium">Risk Model</p><p className="text-sm text-text-mid">Recompute risk scores</p></div></div>
                  <Button className="w-full mt-4" onClick={recompute} disabled={loading}>Recompute Now</Button>
                </Card>
                <Card variant="glass-strong" className="p-4">
                  <div className="flex items-center gap-3"><Database size={24} className="text-primary" /><div><p className="font-medium">Evidence Pipeline</p><p className="text-sm text-text-mid">Refresh evidence scores</p></div></div>
                  <Button variant="outline" className="w-full mt-4">Refresh Evidence</Button>
                </Card>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}