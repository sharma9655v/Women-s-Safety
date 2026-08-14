"use client";

import { AlertCircle, Database, ShieldCheck } from "lucide-react";
import { Drawer } from "@/app/components/ui/Drawer";
import { Progress } from "@/app/components/ui/Progress";
import type { SafetyEvidence } from "@/lib/types";
import { FreshnessBadge } from "./FreshnessBadge";

export function EvidenceDrawer({
  open,
  onClose,
  evidence,
}: {
  open: boolean;
  onClose: () => void;
  evidence: SafetyEvidence | null;
}) {
  if (!evidence) return null;

  return (
    <Drawer open={open} onClose={onClose} title="Evidence Sources">
      <div className="space-y-4">
        {/* Overall */}
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Database className="size-5" aria-hidden />
          </span>
          <div className="flex-1">
            <p className="text-sm font-semibold text-foreground">
              {evidence.sources.length} source
              {evidence.sources.length !== 1 ? "s" : ""}
            </p>
            <FreshnessBadge tier={evidence.freshness.tier} />
          </div>
          <span className="text-sm font-bold text-foreground">
            {Math.round(evidence.confidence_value * 100)}%
          </span>
        </div>

        {/* Sources */}
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wide">Sources</h4>
          {evidence.sources.map((src) => (
            <div
              key={src.id}
              className="flex items-center gap-3 rounded-xl border border-border bg-surface p-3"
            >
              <ShieldCheck className="size-4 text-primary" aria-hidden />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">{src.name}</p>
                <p className="text-[10px] text-text-muted capitalize">{src.kind}</p>
              </div>
              <div className="w-16">
                <Progress
                  value={Math.round(src.reliability * 100)}
                  tone={src.reliability >= 0.7 ? "success" : "warning"}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Conflicts */}
        {evidence.conflicts.length > 0 ? (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wide">
              Conflicts
            </h4>
            {evidence.conflicts.map((c) => (
              <div
                key={`${c.observation_type}-${c.detail}`}
                className="flex items-start gap-2 rounded-xl border border-warning/20 bg-warning/5 p-3"
              >
                <AlertCircle className="mt-0.5 size-4 text-warning" aria-hidden />
                <div>
                  <p className="text-xs font-medium text-foreground capitalize">
                    {c.observation_type.replace(/_/g, " ")}
                  </p>
                  <p className="text-[10px] text-text-muted">{c.detail}</p>
                </div>
              </div>
            ))}
          </div>
        ) : null}

        {/* Coverage */}
        {evidence.coverage !== null ? (
          <div className="rounded-xl border border-border bg-surface p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-text-muted">Evidence coverage</span>
              <span className="text-xs font-semibold text-foreground">
                {Math.round(evidence.coverage * 100)}%
              </span>
            </div>
            <Progress value={Math.round(evidence.coverage * 100)} tone="primary" />
          </div>
        ) : null}

        <p className="text-[10px] text-text-muted text-center pt-2">
          Evidence is aggregated from multiple sources. Quality varies. This is an estimate, not a
          guarantee of safety.
        </p>
      </div>
    </Drawer>
  );
}
