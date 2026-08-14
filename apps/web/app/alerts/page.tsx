"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCard } from "@/app/components/insights/LiveAlertsList";
import { Pill } from "@/app/components/ui/Pill";
import { SkeletonCard } from "@/app/components/ui/Skeleton";
import { fetchAlerts } from "@/lib/api";
import type { Incident } from "@/lib/types";

const SEVERITY = ["all", "high", "moderate", "low"] as const;
const CATEGORIES = [
  "all",
  "harassment",
  "poor_lighting",
  "road_work",
  "crowd_alert",
  "streetlight_not_working",
  "suspicious_activity",
] as const;

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [severity, setSeverity] = useState<(typeof SEVERITY)[number]>("all");
  const [category, setCategory] = useState<(typeof CATEGORIES)[number]>("all");

  useEffect(() => {
    let cancelled = false;
    fetchAlerts()
      .then((a) => {
        if (!cancelled) setAlerts(a);
      })
      .catch(() => {
        if (!cancelled) setError("Alerts are unavailable right now.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(
    () =>
      alerts.filter(
        (a) =>
          (severity === "all" || a.severity === severity) &&
          (category === "all" || a.category === category),
      ),
    [alerts, severity, category],
  );

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-4 p-4 lg:p-6">
        <header>
          <h1 className="text-xl font-bold text-foreground">
            <span className="text-primary">Alerts</span>
          </h1>
          <p className="text-sm text-text-muted">
            Recent community reports near you. Reports are not official warnings.
          </p>
        </header>

        <div className="flex flex-wrap gap-1.5">
          {SEVERITY.map((s) => (
            <Pill key={s} active={severity === s} onClick={() => setSeverity(s)}>
              {s === "all" ? "All severities" : `${s} severity`}
            </Pill>
          ))}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {CATEGORIES.map((c) => (
            <Pill key={c} active={category === c} onClick={() => setCategory(c)}>
              {c === "all" ? "All categories" : c.replace(/_/g, " ")}
            </Pill>
          ))}
        </div>

        {loading ? (
          <div className="space-y-3">
            <SkeletonCard rows={2} />
            <SkeletonCard rows={2} />
          </div>
        ) : error ? (
          <p className="glass rounded-2xl p-4 text-center text-sm text-danger">{error}</p>
        ) : filtered.length === 0 ? (
          <p className="glass rounded-2xl p-4 text-center text-sm text-text-muted">
            No alerts match these filters.
          </p>
        ) : (
          <div className="space-y-2.5">
            {filtered.map((a) => (
              <AlertCard key={a.id} alert={a} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
