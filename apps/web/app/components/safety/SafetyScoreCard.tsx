"use client";

import { ShieldCheck } from "lucide-react";
import { Badge } from "@/app/components/ui/Badge";
import { Card } from "@/app/components/ui/Card";
import { Gauge } from "@/app/components/ui/Gauge";
import { BAND_LABEL } from "@/lib/score";
import type { SafetyScore } from "@/lib/types";

export function SafetyScoreCard({
  score,
  title = "Estimated Safety",
  subtitle,
}: {
  score: SafetyScore;
  title?: string;
  subtitle?: string;
}) {
  const tone =
    score.band === "high"
      ? "success"
      : score.band === "moderate"
        ? "warning"
        : score.band === "low"
          ? "danger"
          : "default";

  return (
    <Card className="flex flex-col items-center gap-3 py-5">
      <div className="flex items-center gap-2">
        <ShieldCheck className="size-4 text-primary" aria-hidden />
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      </div>

      <Gauge value={score.value} max={100} size={110} strokeWidth={8} label={`/ 100`} />

      <Badge tone={tone as "success" | "warning" | "danger" | "default"}>
        {BAND_LABEL[score.band]}
      </Badge>

      <div className="flex items-center gap-3 text-xs text-text-muted">
        <span>Confidence: {score.confidence}</span>
        {score.evidence.coverage !== null ? (
          <span>Coverage: {Math.round(score.evidence.coverage * 100)}%</span>
        ) : null}
      </div>

      {subtitle ? <p className="text-center text-[11px] text-text-muted">{subtitle}</p> : null}
    </Card>
  );
}
