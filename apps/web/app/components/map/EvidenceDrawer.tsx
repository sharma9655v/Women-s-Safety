"use client";
import { ReactNode } from "react";
import { X, ChevronDown } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatDuration, formatDistance, riskBandLabel, riskBandStyle, FRESHNESS_STYLE, freshnessFromAge } from "@/lib/format";

interface EvidenceItem {
  segment_id: number;
  total_observations: number;
  overall_confidence: number;
  overall_freshness: number | null;
  conflicts: string[];
  by_type: Record<string, { observation_type: string; count: number; score: number; freshness: number; confidence: number; conflicts: boolean; source_counts: Record<string, number>; state_counts: Record<string, number>; distinct_source_types: number; corroborated: boolean }>;
  model_version: string;
}

export function EvidenceDrawer({ open, onClose, evidence }: { open: boolean; onClose: () => void; evidence: EvidenceItem | null }) {
  if (!open || !evidence) return null;
  const freshness = freshnessFromAge(evidence.overall_freshness);
  return (
    <div className="fixed inset-0 z-50 flex" onClick={onClose} role="dialog" aria-modal="true">
      <div className="flex-1 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="glass-strong w-full max-w-xl flex flex-col h-full shadow-glass-lg border-l border-line animate-in" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-line">
          <h3 className="font-display font-semibold">Segment Evidence</h3>
          <button onClick={onClose} className="p-1 text-text-low hover:text-text-hi hover:bg-white/5" aria-label="Close"><svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg></button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant={["high","moderate","low","limited"].includes(String(evidence.by_type?.[Object.keys(evidence.by_type)[0]]?.score ?? "")) ? "default" : ("success" as const)}>Segment #{evidence.segment_id}</Badge>
            <Badge className={FRESHNESS_STYLE[freshness.tier]}>{freshness.label}</Badge>
            <Badge variant="default">{evidence.total_observations} observations</Badge>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="glass p-3 rounded-lg"><p className="text-xs text-text-low">Confidence</p><p className="font-semibold text-text-hi">{(evidence.overall_confidence * 100).toFixed(0)}%</p></div>
            <div className="glass p-3 rounded-lg"><p className="text-xs text-text-low">Model</p><p className="font-mono text-sm text-text-mid">{evidence.model_version}</p></div>
          </div>
          {evidence.conflicts.length > 0 && (
            <div className="glass p-3 rounded-lg border-danger/30">
              <p className="text-sm text-danger font-medium">Conflicts</p>
              <ul className="mt-1 space-y-1 text-sm text-text-mid">{evidence.conflicts.map((c, i) => <li key={i}>• {c}</li>)}</ul>
            </div>
          )}
          <div className="space-y-3">
            {Object.entries(evidence.by_type).map(([type, data]) => (
              <details key={type} className="group glass p-3 rounded-lg">
                <summary className="flex items-center justify-between cursor-pointer list-none">
                  <div className="flex items-center gap-2">
                    <span className="font-medium capitalize">{type.replace(/_/g, " ")}</span>
                    <Badge variant={data.conflicts ? "warn" : "success" as const}>{data.conflicts ? "Conflict" : "Corroborated"}</Badge>
                  </div>
                  <svg width={16} height={16} className="transition-transform group-open:rotate-180 text-text-low" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 9l6 6 6-6"/></svg>
                </summary>
                <div className="mt-3 space-y-2 text-sm text-text-mid border-t border-line pt-3">
                  <div className="grid gap-1 sm:grid-cols-2">
                    <span>Count</span><span className="text-text-hi">{data.count}</span>
                    <span>Score</span><span className="text-text-hi">{data.score.toFixed(2)}</span>
                    <span>Freshness (hrs)</span><span className="text-text-hi">{data.freshness.toFixed(1)}</span>
                    <span>Confidence</span><span className="text-text-hi">{(data.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div className="pt-2 border-t border-line">
                    <span className="text-xs text-text-low">Sources:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {Object.entries(data.source_counts).map(([src, cnt]) => <Badge key={src} variant="default" className="text-xs">{src}: {cnt}</Badge>)}
                    </div>
                  </div>
                </div>
              </details>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}