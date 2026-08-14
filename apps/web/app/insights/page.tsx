"use client";

import { Lightbulb, Radio, ShieldCheck, Unplug } from "lucide-react";
import { type ReactNode, useCallback, useEffect, useState } from "react";
import { LiveAlertsList } from "@/app/components/insights/LiveAlertsList";
import { type HeatZone, SafetyHeatmapPanel } from "@/app/components/insights/SafetyHeatmapPanel";
import { Reveal } from "@/app/components/motion/Reveal";
import { SafetyScoreCard } from "@/app/components/safety/SafetyScoreCard";
import { ScoreTrendCard } from "@/app/components/safety/ScoreTrendCard";
import { Card, CardHeader } from "@/app/components/ui/Card";
import { SkeletonCard } from "@/app/components/ui/Skeleton";
import { fetchAreaSafety, fetchHeatmapZones, fetchIncidents } from "@/lib/api";
import type { AreaSafety, Incident, SafetyScore } from "@/lib/types";

const SKELETON_SLOTS = [0, 1, 2, 3, 4, 5];

function StatTile({
  icon,
  label,
  value,
  tone,
  delay = 0,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  tone: string;
  delay?: number;
}) {
  return (
    <Reveal delay={delay}>
      <Card className="card-hover flex items-center gap-3">
        <span className={`flex size-10 shrink-0 items-center justify-center rounded-xl ${tone}`}>
          {icon}
        </span>
        <div className="min-w-0">
          <p className="text-lg font-bold text-foreground">{value}</p>
          <p className="truncate text-xs text-text-muted">{label}</p>
        </div>
      </Card>
    </Reveal>
  );
}

export default function InsightsPage() {
  const [area, setArea] = useState<AreaSafety | null>(null);
  const [score, setScore] = useState<SafetyScore | null>(null);
  const [zones, setZones] = useState<HeatZone[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchAreaSafety(), fetchHeatmapZones(), fetchIncidents()])
      .then(([a, z, i]) => {
        if (cancelled) return;
        setArea(a);
        setScore(a.score);
        setZones(z.zones);
        setIncidents(i);
      })
      .catch(() => {
        if (!cancelled) {
          setArea(null);
          setScore(null);
          setZones([]);
          setIncidents([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const focusZoneOnMap = useCallback(() => {
    document
      .getElementById("heatmap-card")
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, []);

  if (loading) {
    return (
      <div className="grid h-full grid-cols-1 gap-4 overflow-y-auto p-4 lg:grid-cols-3">
        {SKELETON_SLOTS.map((slot) => (
          <SkeletonCard key={slot} rows={4} />
        ))}
      </div>
    );
  }

  if (!area || !score) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="glass max-w-md rounded-2xl p-8 text-center">
          <span className="mx-auto mb-3 flex size-12 items-center justify-center rounded-full bg-surface-hover text-text-muted">
            <ShieldCheck className="size-5" aria-hidden />
          </span>
          <p className="text-sm text-text-muted">
            Insights are unavailable right now — the analytics service isn&apos;t responding.
          </p>
        </div>
      </div>
    );
  }

  const freshShare = Math.round((area.score.evidence.coverage ?? 0) * 100);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl space-y-4 p-4 lg:p-6">
        <header>
          <h1 className="text-xl font-bold text-foreground">
            Safety <span className="text-primary">Insights</span>
          </h1>
          <p className="text-sm text-text-muted">
            Estimates for {area.area_name} built from verified reports and public evidence.
          </p>
        </header>

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatTile
            icon={<ShieldCheck className="size-5" aria-hidden />}
            label="Area Estimated Safety"
            value={`${score.value}/100`}
            tone="bg-primary/12 text-primary"
          />
          <StatTile
            icon={<Radio className="size-5" aria-hidden />}
            label="Incidents (7 days)"
            value={String(area.recent_incidents)}
            tone="bg-emergency/12 text-emergency"
            delay={0.06}
          />
          <StatTile
            icon={<Lightbulb className="size-5" aria-hidden />}
            label="Lighting evidence"
            value={area.lighting_summary}
            tone="bg-success/12 text-success"
            delay={0.12}
          />
          <StatTile
            icon={<Unplug className="size-5" aria-hidden />}
            label="Evidence coverage"
            value={`${freshShare}%`}
            tone="bg-info/12 text-info"
            delay={0.18}
          />
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <SafetyScoreCard score={score} title="Area Estimated Safety" />
          <div className="lg:col-span-2">
            <ScoreTrendCard points={area.by_time_of_day} />
          </div>
        </div>

        <div id="heatmap-card" className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <SafetyHeatmapPanel zones={zones} onFocusZone={focusZoneOnMap} />
          </div>
          <div className="lg:col-span-2">
            <Card>
              <CardHeader
                title="What the evidence says"
                subtitle="How this score is built — nothing is guaranteed"
              />
              <ul className="space-y-3 text-sm text-text-secondary">
                <li className="flex items-start gap-2.5">
                  <span className="mt-1 size-2 shrink-0 rounded-full bg-success" />
                  <span>
                    <strong className="text-foreground">Crowd level: {area.crowd}.</strong> Observed
                    from transit data and community check-ins; changes throughout the day.
                  </span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="mt-1 size-2 shrink-0 rounded-full bg-warning" />
                  <span>
                    <strong className="text-foreground">Lighting: {area.lighting_summary}.</strong>{" "}
                    Streetlight data comes from city sensors and reports; some areas have no
                    coverage.
                  </span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="mt-1 size-2 shrink-0 rounded-full bg-emergency" />
                  <span>
                    <strong className="text-foreground">
                      Recent incidents: {area.recent_incidents}.
                    </strong>{" "}
                    {area.recent_incidents > 0
                      ? "Community reports in the last week. Not all are verified."
                      : "No recent community reports."}
                  </span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="mt-1 size-2 shrink-0 rounded-full bg-info" />
                  <span>
                    <strong className="text-foreground">Confidence: {score.confidence}.</strong>{" "}
                    Only {freshShare}% of this area is covered by fresh evidence — the rest is
                    interpolated.
                  </span>
                </li>
              </ul>
            </Card>
          </div>
        </div>

        <div className="h-96 lg:h-80">
          <LiveAlertsList alerts={incidents} title="Recent Incident Reports" />
        </div>
      </div>
    </div>
  );
}
