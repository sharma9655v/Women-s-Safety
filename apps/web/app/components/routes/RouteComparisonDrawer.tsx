"use client";

import { Clock, MoveRight, ShieldCheck } from "lucide-react";
import { Button } from "@/app/components/ui/Button";
import { Drawer } from "@/app/components/ui/Drawer";
import { Progress } from "@/app/components/ui/Progress";
import { formatDistance, formatDuration } from "@/lib/format";
import type { RouteCandidate } from "@/lib/types";

export function RouteComparisonDrawer({
  open,
  onClose,
  routes,
  onChoose,
}: {
  open: boolean;
  onClose: () => void;
  routes: RouteCandidate[];
  onChoose: (id: string) => void;
}) {
  if (routes.length === 0) return null;

  const maxDist = Math.max(...routes.map((r) => r.distance_m));
  const maxDur = Math.max(...routes.map((r) => r.duration_s));

  return (
    <Drawer open={open} onClose={onClose} title="Compare routes">
      <div className="space-y-4">
        {routes.map((route) => (
          <div key={route.id} className="rounded-2xl border border-border bg-surface p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="flex items-center gap-1.5 text-sm font-bold text-foreground">
                {route.title}
                {route.label === "recommended" ? (
                  <ShieldCheck className="size-3.5 text-accent" aria-hidden />
                ) : null}
              </h3>
              <span className="text-lg font-bold text-foreground">
                {route.safety.value}
                <span className="text-xs text-text-muted">/100</span>
              </span>
            </div>

            <div className="space-y-2">
              <div>
                <div className="flex items-center justify-between text-xs text-text-muted mb-1">
                  <span className="flex items-center gap-1">
                    <ShieldCheck className="size-3" aria-hidden /> Estimated Safety
                  </span>
                  <span>{route.safety.value}%</span>
                </div>
                <Progress
                  value={route.safety.value}
                  tone={
                    route.safety.value >= 70
                      ? "success"
                      : route.safety.value >= 45
                        ? "warning"
                        : "danger"
                  }
                />
              </div>

              <div>
                <div className="flex items-center justify-between text-xs text-text-muted mb-1">
                  <span className="flex items-center gap-1">
                    <MoveRight className="size-3" aria-hidden /> Distance
                  </span>
                  <span>{formatDistance(route.distance_m)}</span>
                </div>
                <Progress value={route.distance_m} max={maxDist} tone="primary" />
              </div>

              <div>
                <div className="flex items-center justify-between text-xs text-text-muted mb-1">
                  <span className="flex items-center gap-1">
                    <Clock className="size-3" aria-hidden /> Duration
                  </span>
                  <span>{formatDuration(route.duration_s)}</span>
                </div>
                <Progress value={route.duration_s} max={maxDur} tone="primary" />
              </div>
            </div>

            <Button variant="outline" size="sm" fullWidth onClick={() => onChoose(route.id)}>
              Choose this route
            </Button>
          </div>
        ))}

        <p className="text-center text-[10px] text-text-muted">
          Safety scores are estimates based on available evidence. They are not guarantees.
        </p>
      </div>
    </Drawer>
  );
}
