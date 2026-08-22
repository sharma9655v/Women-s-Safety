"use client";

import { CheckCircle2, Database, ExternalLink, GitBranch, Lock, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { Card } from "@/app/components/ui/Card";
import { apiUrl } from "@/lib/api";

type Status = "live" | "gated" | "none";

interface Source {
  name: string;
  status: Status;
  usedFor: string;
  detail: string;
  link?: string;
}

const SOURCES: Source[] = [
  {
    name: "OpenStreetMap road network",
    status: "live",
    usedFor: "Routing (OSRM), 1.88M road segments, road type & lit tags",
    detail:
      "Loaded from a Delhi extract into PostGIS; OSRM serves routing. Road-type and lighting attributes feed the risk model at query time.",
    link: "https://www.openstreetmap.org/",
  },
  {
    name: "OpenStreetMap facilities",
    status: "live",
    usedFor: "Safe-place finder, emergency-facility distance in risk estimates",
    detail:
      "3,927 indexed facilities (police, hospitals, fire stations, transit, public places) served by the facilities store.",
    link: "https://www.openstreetmap.org/",
  },
  {
    name: "Community reports (this app)",
    status: "live",
    usedFor: "Evidence engine: freshness, conflicts, per-segment risk",
    detail:
      "Anonymous, rate-limited reports surface live as user_report observations. Redaction and encryption at rest; identity never collected.",
  },
  {
    name: "Deterministic risk model",
    status: "live",
    usedFor: "Routing decisions, 'why this score' views",
    detail:
      "Rule-based baseline (deterministic-baseline-v1). Pure function of evidence, road attributes and time-of-day — reproducible, explainable.",
  },
  {
    name: "ML pipeline",
    status: "gated",
    usedFor: "Future evidence scoring (not used in routing today)",
    detail:
      "Exists behind a validation gate: it opens only once enough VERIFIED evidence spans enough days. Until then the UI is honest about it being unavailable.",
  },
  {
    name: "Government / municipal feeds",
    status: "none",
    usedFor: "—",
    detail:
      "Not connected. The Civic Ops worklist is built from our own evidence instead of claiming a live data.gov.in integration that does not exist.",
  },
  {
    name: "Crowd-sourced data (commute apps, forums)",
    status: "none",
    usedFor: "—",
    detail:
      "Not connected. Where the UI could show crowd levels, it says 'not available' rather than inventing values.",
  },
  {
    name: "Weather",
    status: "none",
    usedFor: "—",
    detail:
      "No weather API key is configured. The risk model deliberately excludes weather rather than guessing.",
  },
];

const STATUS_META: Record<Status, { label: string; className: string }> = {
  live: { label: "Live", className: "bg-success/12 text-success" },
  gated: { label: "Gated (validated)", className: "bg-warning/12 text-warning" },
  none: { label: "Not connected", className: "bg-danger/12 text-danger" },
};

export default function DataSourcesPage() {
  const [apiHealthy, setApiHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${apiUrl()}/api/models/current`, { signal: AbortSignal.timeout(8000) })
      .then((r) => {
        if (!cancelled) setApiHealthy(r.ok);
      })
      .catch(() => {
        if (!cancelled) setApiHealthy(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl space-y-4 p-4 lg:p-6">
        <header>
          <h1 className="flex items-center gap-2 text-xl font-bold text-foreground">
            <Database className="size-5 text-primary" aria-hidden />
            Data <span className="text-primary">Sources</span>
          </h1>
          <p className="text-sm text-text-muted">
            An honest integration matrix: what is live, what is gated behind validation, and what is
            deliberately not connected — with the live API status checked at load.
          </p>
        </header>

        <Card className="flex items-center gap-3">
          <span
            className={`flex size-10 shrink-0 items-center justify-center rounded-xl ${
              apiHealthy === true
                ? "bg-success/15 text-success"
                : apiHealthy === false
                  ? "bg-danger/15 text-danger"
                  : "bg-surface-hover text-text-muted"
            }`}
          >
            {apiHealthy === true ? (
              <CheckCircle2 className="size-5" aria-hidden />
            ) : apiHealthy === false ? (
              <TriangleAlert className="size-5" aria-hidden />
            ) : (
              <GitBranch className="size-5" aria-hidden />
            )}
          </span>
          <div>
            <p className="text-sm font-semibold text-foreground">
              Live API:{" "}
              {apiHealthy === true
                ? "reachable"
                : apiHealthy === false
                  ? "unreachable"
                  : "checking…"}
            </p>
            <p className="text-xs text-text-muted">
              {apiHealthy === true
                ? `All pages above pull from this instance (${apiUrl()}).`
                : "Data pages will show empty/offline states honestly instead of stale values."}
            </p>
          </div>
        </Card>

        <div className="space-y-3">
          {SOURCES.map((s) => {
            const meta = STATUS_META[s.status];
            return (
              <Card key={s.name} className="space-y-1.5">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-foreground">{s.name}</p>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${meta.className}`}
                  >
                    {meta.label}
                  </span>
                </div>
                <p className="text-xs font-medium text-primary">{s.usedFor}</p>
                <p className="text-xs leading-relaxed text-text-secondary">{s.detail}</p>
                {s.link ? (
                  <a
                    href={s.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[11px] text-text-muted transition-colors hover:text-primary"
                  >
                    <ExternalLink className="size-3" aria-hidden />
                    {s.link.replace("https://", "")}
                  </a>
                ) : null}
              </Card>
            );
          })}
        </div>

        <p className="flex items-start gap-2 rounded-2xl border border-border bg-surface/50 px-4 py-3 text-xs leading-relaxed text-text-muted">
          <Lock className="mt-0.5 size-3.5 shrink-0 text-primary" aria-hidden />
          Everything above is verifiable from this deployment: routing, facilities and evidence
          endpoints return live data, and the models endpoint reports the exact model version in
          use. Nothing here claims an integration that does not exist.
        </p>
      </div>
    </div>
  );
}
