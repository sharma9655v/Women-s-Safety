"use client";

import { AlertCircle, Clock, MapPin } from "lucide-react";
import { Badge } from "@/app/components/ui/Badge";
import { Card, CardHeader } from "@/app/components/ui/Card";
import { timeAgo } from "@/lib/format";
import type { Incident } from "@/lib/types";

const SEVERITY_TONE: Record<string, "danger" | "warning" | "info" | "default"> = {
  critical: "danger",
  high: "danger",
  moderate: "warning",
  low: "info",
};

export function AlertCard({ alert }: { alert: Incident }) {
  const tone = SEVERITY_TONE[alert.severity] ?? "default";

  return (
    <div className="flex gap-3 rounded-xl border border-border bg-surface p-3 transition-colors duration-200 hover:border-border-glow hover:bg-surface-hover">
      <span
        className={`mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg ${
          tone === "danger"
            ? "bg-emergency/12 text-emergency"
            : tone === "warning"
              ? "bg-warning/12 text-warning"
              : "bg-info/12 text-info"
        }`}
      >
        <AlertCircle className="size-4" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-foreground capitalize">
          {alert.category.replace(/_/g, " ")}
        </p>
        <p className="mt-0.5 text-xs text-text-muted line-clamp-2">{alert.summary}</p>
        <div className="mt-1.5 flex items-center gap-2 text-[10px] text-text-muted">
          <span className="flex items-center gap-0.5">
            <Clock className="size-3" aria-hidden />
            {timeAgo(alert.reported_at)}
          </span>
          <span className="flex items-center gap-0.5">
            <MapPin className="size-3" aria-hidden />
            {alert.location.name}
          </span>
          <Badge tone={tone}>{alert.severity}</Badge>
        </div>
      </div>
    </div>
  );
}

export function LiveAlertsList({
  alerts,
  title = "Live Alerts",
}: {
  alerts: Incident[];
  title?: string;
}) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader title={title} subtitle="Community reports — not official warnings" />
      {alerts.length === 0 ? (
        <p className="py-6 text-center text-xs text-text-muted">No recent alerts available.</p>
      ) : (
        <div className="flex-1 space-y-2 overflow-y-auto">
          {alerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </Card>
  );
}
