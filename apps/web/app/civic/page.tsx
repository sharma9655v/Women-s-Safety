"use client";

import { Building2, ExternalLink, Flame, Lightbulb, MapPin, ShieldAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Card, CardHeader } from "@/app/components/ui/Card";
import { Pill } from "@/app/components/ui/Pill";
import { SkeletonCard } from "@/app/components/ui/Skeleton";
import { fetchAreaComparisons, fetchHeatmapZones, fetchIncidents, fetchLighting } from "@/lib/api";
import type { AreaSafety, Incident, LightingObservation } from "@/lib/types";

type LightingWithCoords = LightingObservation & { lat: number; lon: number };

function mapsUrl(lat: number, lon: number): string {
  return `https://www.google.com/maps?q=${lat.toFixed(5)},${lon.toFixed(5)}`;
}

export default function CivicPage() {
  const [lighting, setLighting] = useState<LightingWithCoords[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [areas, setAreas] = useState<AreaSafety[]>([]);
  const [zones, setZones] = useState<{ name: string; lat: number; lon: number; level: number }[]>(
    [],
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchLighting(), fetchIncidents(), fetchAreaComparisons(), fetchHeatmapZones()])
      .then(([l, i, a, h]) => {
        if (cancelled) return;
        setLighting(l);
        setIncidents(i);
        setAreas(a);
        setZones(h.zones);
      })
      .catch(() => {
        if (!cancelled) setError("Civic data is unavailable right now.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const failures = useMemo(() => lighting.filter((l) => l.working === false), [lighting]);
  const totalLighting = lighting.length;

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const inc of incidents) {
      counts[inc.category] = (counts[inc.category] ?? 0) + 1;
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, [incidents]);

  const highestRiskZone = useMemo(() => {
    if (zones.length === 0) return null;
    return [...zones].sort((a, b) => b.level - a.level)[0];
  }, [zones]);

  const lowestArea = useMemo(() => {
    if (areas.length === 0) return null;
    return [...areas].sort((a, b) => (a.score.value ?? 0) - (b.score.value ?? 0))[0];
  }, [areas]);

  if (loading) {
    return (
      <div className="grid h-full grid-cols-1 gap-4 overflow-y-auto p-4 lg:grid-cols-3">
        <SkeletonCard rows={4} />
        <SkeletonCard rows={4} />
        <SkeletonCard rows={4} />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl space-y-4 p-4 lg:p-6">
        <header>
          <h1 className="flex items-center gap-2 text-xl font-bold text-foreground">
            <Building2 className="size-5 text-primary" aria-hidden />
            Civic <span className="text-primary">Operations</span>
          </h1>
          <p className="text-sm text-text-muted">
            An actionable worklist built from the same evidence the route planner uses — for
            streetlight repairs and patrol planning. Illustrative demo data.
          </p>
        </header>

        {error ? (
          <p className="glass rounded-2xl p-4 text-center text-sm text-danger">{error}</p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <div className="glass rounded-2xl p-4">
                <p className="flex items-center gap-1.5 text-xs text-text-muted">
                  <Lightbulb className="size-3.5" aria-hidden /> Streetlight failures
                </p>
                <p className="mt-1 text-2xl font-bold text-warning">{failures.length}</p>
              </div>
              <div className="glass rounded-2xl p-4">
                <p className="flex items-center gap-1.5 text-xs text-text-muted">
                  <ShieldAlert className="size-3.5" aria-hidden /> Incident reports
                </p>
                <p className="mt-1 text-2xl font-bold text-emergency">{incidents.length}</p>
              </div>
              <div className="glass rounded-2xl p-4">
                <p className="flex items-center gap-1.5 text-xs text-text-muted">
                  <Flame className="size-3.5" aria-hidden /> Highest-risk zone
                </p>
                <p className="mt-1 truncate text-sm font-bold text-foreground">
                  {highestRiskZone
                    ? `${highestRiskZone.name} (${Math.round(highestRiskZone.level * 100)}%)`
                    : "—"}
                </p>
              </div>
              <div className="glass rounded-2xl p-4">
                <p className="flex items-center gap-1.5 text-xs text-text-muted">
                  <MapPin className="size-3.5" aria-hidden /> Priority area
                </p>
                <p className="mt-1 truncate text-sm font-bold text-foreground">
                  {lowestArea ? lowestArea.area_name : "—"}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader
                  title="Streetlight failure worklist"
                  subtitle="Open each in maps to dispatch a crew"
                />
                {failures.length === 0 ? (
                  <p className="py-6 text-center text-xs text-text-muted">
                    No streetlight failures reported in the current view.
                  </p>
                ) : (
                  <ul className="max-h-80 space-y-1.5 overflow-y-auto pr-1">
                    {failures.map((f) => (
                      <li
                        key={`${f.lat.toFixed(5)}-${f.lon.toFixed(5)}-${f.observed_at ?? "na"}`}
                        className="flex items-center gap-2 rounded-xl border border-border/60 bg-surface/50 px-3 py-2"
                      >
                        <Lightbulb className="size-3.5 shrink-0 text-warning" aria-hidden />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-xs font-medium text-foreground">
                            {f.status_label}
                          </p>
                          <p className="text-[11px] text-text-muted">
                            {f.lat.toFixed(5)}, {f.lon.toFixed(5)} · {f.source}
                          </p>
                        </div>
                        <a
                          href={mapsUrl(f.lat, f.lon)}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label={`Open streetlight failure location in maps`}
                          className="flex size-7 shrink-0 items-center justify-center rounded-lg text-text-muted transition-colors hover:bg-surface-hover hover:text-primary"
                        >
                          <ExternalLink className="size-3.5" aria-hidden />
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>

              <div className="space-y-4">
                <Card>
                  <CardHeader title="Incident reports by category" subtitle="For patrol planning" />
                  <ul className="space-y-2">
                    {categoryCounts.map(([cat, count]) => (
                      <li key={cat} className="flex items-center gap-3">
                        <Pill active={false} onClick={() => {}}>
                          {cat.replace(/_/g, " ")}
                        </Pill>
                        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-hover">
                          <div
                            className="h-full rounded-full bg-emergency"
                            style={{ width: `${Math.round((count / incidents.length) * 100)}%` }}
                          />
                        </div>
                        <span className="w-8 text-right text-xs font-semibold text-foreground">
                          {count}
                        </span>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-3 text-xs text-text-muted">
                    {totalLighting} lighting observations in view, {failures.length} non-working.
                  </p>
                </Card>

                <Card>
                  <CardHeader title="Priority areas" subtitle="Lowest estimated safety first" />
                  <ul className="space-y-1.5">
                    {areas
                      .slice()
                      .sort((a, b) => (a.score.value ?? 0) - (b.score.value ?? 0))
                      .slice(0, 5)
                      .map((a) => (
                        <li
                          key={a.area_name}
                          className="flex items-center justify-between rounded-xl border border-border/60 bg-surface/50 px-3 py-2"
                        >
                          <span className="text-xs font-medium text-foreground">{a.area_name}</span>
                          <span
                            className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                              a.score.band === "low"
                                ? "bg-emergency/12 text-emergency"
                                : a.score.band === "moderate"
                                  ? "bg-warning/12 text-warning"
                                  : "bg-success/12 text-success"
                            }`}
                          >
                            {a.score.value ?? 0}/100
                          </span>
                        </li>
                      ))}
                  </ul>
                </Card>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
