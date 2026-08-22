"use client";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Tabs } from "@/components/ui/Tabs";
import { Shield, Cpu, Database, Loader2, CheckCircle, XCircle, AlertTriangle, FileText, Download, ExternalLink, GitBranch, Globe, Eye, BarChart2, Brain, Zap } from "lucide-react";

export default function ModelsPage() {
  const { data: models, mutate } = useQuery("models-page", () => api.models(), { revalidateMs: 60_000 });

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      <div className="p-4 sm:p-6 border-b border-line">
        <div className="mx-auto max-w-5xl">
          <h1 className="font-display text-2xl font-bold">Model Registry & Transparency</h1>
          <p className="text-sm text-text-mid">Open model governance: every checkpoint, its status, and how it feeds routing decisions.</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="mx-auto max-w-5xl space-y-6">
          {/* ML Gate */}
          {models && (
            <Card variant="glass">
              <h3 className="font-medium flex items-center gap-2 mb-4"><Shield size={20} className="text-primary" /> ML Gate Status</h3>
              <div className="grid gap-4 sm:grid-cols-4">
                <div className="glass p-4 rounded-xl text-center"><BarChart2 size={24} className="mx-auto text-accent mb-2" /><p className="font-display text-2xl font-bold">{models.ml_gate.open ? "OPEN" : "CLOSED"}</p><p className="text-xs text-text-mid">Gate</p></div>
                <div className="glass p-4 rounded-xl text-center"><CheckCircle size={24} className="mx-auto text-safe mb-2" /><p className="font-display text-2xl font-bold">{models.ml_gate.verified_observations}</p><p className="text-xs text-text-mid">Verified Obs.</p></div>
                <div className="glass p-4 rounded-xl text-center"><Database size={24} className="mx-auto text-primary mb-2" /><p className="font-display text-2xl font-bold">{models.ml_gate.span_days ?? "—"}</p><p className="text-xs text-text-mid">Span (days)</p></div>
                <div className="glass p-4 rounded-xl text-center"><Zap size={24} className="mx-auto text-warn mb-2" /><p className="font-display text-2xl font-bold">{models.ml_gate.min_verified_observations}</p><p className="text-xs text-text-mid">Min Required</p></div>
              </div>
              <div className="mt-4 glass p-3 rounded-xl text-sm text-text-mid">
                Min verified: {models.ml_gate.min_verified_observations} • Min span: {models.ml_gate.min_span_days} days
              </div>
            </Card>
          )}

          {/* Risk & Evidence Models */}
          {models && (
            <Card variant="glass">
              <h3 className="font-medium flex items-center gap-2 mb-4"><Brain size={20} className="text-info" /> Active Models</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <ModelCard title="Risk Model" version={models.risk_model} type="Risk scoring" icon={<Brain size={24} className="text-info" />} />
                <ModelCard title="Evidence Model" version={models.evidence_model} type="Evidence fusion" icon={<Database size={24} className="text-primary" />} />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {models.dataset_versions.map((v, i) => <Badge key={i} variant="default">{v}</Badge>)}
              </div>
            </Card>
          )}

          {/* CV Models */}
          {models && (
            <Tabs
              defaultValue="cv"
              items={[
                { value: "cv", label: "CV Models" },
                { value: "sources", label: "Data Sources" },
              ]}
              render={(tab) => (
                <Card variant="glass">
                  <h3 className="font-medium flex items-center gap-2 mb-4">{tab === "cv" && <><Eye size={20} className="text-warn" /> Computer Vision Models</>} {tab === "sources" && <><Globe size={20} className="text-accent" /> Data Sources & Provenance</>}</h3>

                  {tab === "cv" && (
                    <div className="space-y-3">
                      {models.cv_models.length === 0 ? (
                        <p className="text-text-mid text-center py-8">No CV models registered</p>
                      ) : (
                        models.cv_models.map(m => (
                          <div key={m.name} className="glass p-4 rounded-xl">
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <Badge variant={m.status === "PRODUCTION" ? "success" : m.status === "AVAILABLE" ? "info" : m.status === "EXPERIMENTAL" ? "warn" : "danger"}> {m.status} </Badge>
                                  <Badge variant="default">{m.kind}</Badge>
                                  <Badge variant="default">{m.framework}</Badge>
                                </div>
                                <p className="font-medium mt-1">{m.name} v{m.version}</p>
                                <p className="text-xs text-text-mid mt-1">Checkpoint: {m.checkpoint_path}</p>
                                <div className="flex flex-wrap gap-2 mt-2">
                                  {Object.entries(m.metrics).map(([k, v]) => <Badge key={k} variant="default" className="text-xs">{k}: {Number(v).toFixed(3)}</Badge>)}
                                </div>
                              </div>
                              <div className="flex gap-2">
                                <Button variant="outline" size="sm"><Eye size={14} /> Details</Button>
                                <Button variant="outline" size="sm"><ExternalLink size={14} /> Registry</Button>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  {tab === "sources" && (
                    <div className="space-y-3">
                      <p className="text-sm text-text-mid">Data sources feeding the safety engine. Each source is versioned and auditable.</p>
                      <div className="grid gap-3 sm:grid-cols-2">
                        <SourceCard name="OpenStreetMap" type="Road network & POIs" version="2026-08" status="live" icon={<Globe size={20} />} />
                        <SourceCard name="Community Reports" type="Verified incidents" version="v1.2" status="live" icon={<Shield size={20} />} />
                        <SourceCard name="Lighting Survey" type="Streetlight status" version="2026-Q2" status="aging" icon={<Zap size={20} />} />
                        <SourceCard name="Traffic Cameras" type="Crowd density" version="v0.9" status="experimental" icon={<Eye size={20} />} />
                      </div>
                    </div>
                  )}
                </Card>
              )}
            />
          )}

          {/* Footer transparency */}
          <Card variant="glass" className="border-primary/20">
            <h3 className="font-medium flex items-center gap-2 mb-4"><Shield size={20} className="text-primary" /> Transparency & Reproducibility</h3>
            <ul className="space-y-2 text-sm text-text-mid">
              <li className="flex items-center gap-2"><CheckCircle size={16} className="text-safe" /> All model checkpoints listed in <code className="font-mono bg-surface-elevated px-1 rounded">models/registry.json</code></li>
              <li className="flex items-center gap-2"><CheckCircle size={16} className="text-safe" /> ML Gate criteria public: min {models?.ml_gate.min_verified_observations} verified observations over {models?.ml_gate.min_span_days} days</li>
              <li className="flex items-center gap-2"><CheckCircle size={16} className="text-safe" /> Risk model version: <code className="font-mono bg-surface-elevated px-1 rounded">{models?.risk_model}</code></li>
              <li className="flex items-center gap-2"><CheckCircle size={16} className="text-safe" /> Evidence model version: <code className="font-mono bg-surface-elevated px-1 rounded">{models?.evidence_model}</code></li>
              <li className="flex items-center gap-2"><CheckCircle size={16} className="text-safe" /> CV models only deployed after <span className="font-medium">VALIDATION_REQUIRED → PRODUCTION</span> promotion</li>
              <li className="flex items-center gap-2"><CheckCircle size={16} className="text-safe" /> Dataset versions tracked: {models?.dataset_versions.join(", ") || "—"}</li>
            </ul>
            <div className="mt-4 flex gap-2">
              <Button variant="outline"><FileText size={16} /> View Full Registry (JSON)</Button>
              <Button variant="outline"><GitBranch size={16} /> Source on GitHub</Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function ModelCard({ title, version, type, icon }: { title: string; version: string; type: string; icon: React.ReactNode }) {
  return (
    <div className="glass p-4 rounded-xl">
      <div className="flex items-center gap-3 mb-2">{icon}<div><p className="font-medium">{title}</p><p className="text-xs text-text-mid">{type}</p></div></div>
      <div className="flex items-center justify-between">
        <span className="font-mono text-lg">{version}</span>
        <Badge variant="info">Active</Badge>
      </div>
    </div>
  );
}

function SourceCard({ name, type, version, status, icon }: { name: string; type: string; version: string; status: "live" | "aging" | "experimental"; icon: React.ReactNode }) {
  const statusColors = { live: "success", aging: "warn", experimental: "info" } as const;
  return (
    <div className="glass p-4 rounded-xl">
      <div className="flex items-center gap-3 mb-2">{icon}<div><p className="font-medium">{name}</p><p className="text-xs text-text-mid">{type}</p></div></div>
      <div className="flex items-center justify-between">
        <span className="font-mono text-sm">{version}</span>
        <Badge variant={statusColors[status]}>{status}</Badge>
      </div>
    </div>
  );
}