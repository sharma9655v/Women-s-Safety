"use client";

import { Loader2, Moon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { requestRoutes } from "@/lib/api";
import type { RouteCandidate, SafetyPreference } from "@/lib/types";

const NIGHT_HOUR = 22;

function formatRisk(r: RouteCandidate): number {
  if (r.risk_probability !== undefined) return r.risk_probability;
  return (100 - (r.safety?.value ?? 50)) / 100;
}

/**
 * Honest time-of-day comparison: replans the same trip at 22:00 IST through
 * the real routing API and compares the selected route's risk. No invented
 * numbers — the chip appears only when the model actually says the route is
 * riskier at night.
 */
export function RiskierTonightChip({
  route,
  origin,
  destination,
  mode,
  preference,
}: {
  route: RouteCandidate | null;
  origin: { lat: number; lon: number } | null;
  destination: { lat: number; lon: number } | null;
  mode: string;
  preference: SafetyPreference;
}) {
  const [nightRoute, setNightRoute] = useState<RouteCandidate | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const lastKey = useRef("");

  useEffect(() => {
    if (!route || !origin || !destination) return;
    const key = `${origin.lat},${origin.lon}->${destination.lat},${destination.lon}:${mode}:${preference}`;
    if (key === lastKey.current) return;
    lastKey.current = key;
    let cancelled = false;
    setLoading(true);
    setFailed(false);
    requestRoutes({
      origin,
      destination,
      mode: mode as "walking" | "driving" | "cycling",
      safety_preference: preference,
      hour_ist: NIGHT_HOUR,
    })
      .then((nightRoutes) => {
        if (cancelled) return;
        const matched =
          nightRoutes.find((r) => r.id === route.id) ??
          nightRoutes.find((r) => r.title === route.title) ??
          nightRoutes[0] ??
          null;
        setNightRoute(matched);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [route, origin, destination, mode, preference]);

  if (!route || !origin || !destination || loading || failed || !nightRoute) {
    if (!route || !origin || !destination) return null;
    if (loading) {
      return (
        <p className="flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-2 text-[11px] text-text-muted">
          <Loader2 className="size-3 animate-spin" aria-hidden /> Comparing night-time risk…
        </p>
      );
    }
    return null;
  }

  const now = formatRisk(route);
  const night = formatRisk(nightRoute);
  const pct = (night - now) * 100;
  const riskier = pct > 0.5;

  if (!riskier) {
    return (
      <p className="flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-2 text-[11px] text-text-muted">
        <Moon className="size-3.5 text-primary" aria-hidden />
        Similar risk at night (model estimate at 22:00 IST, not a guarantee)
      </p>
    );
  }

  return (
    <p className="flex items-center gap-1.5 rounded-xl border border-warning/25 bg-warning/5 px-3 py-2 text-[11px] font-medium text-warning">
      <Moon className="size-3.5" aria-hidden />
      Riskier tonight: about {Math.max(1, Math.round(pct))}% higher risk at 22:00 IST
      <span className="font-normal text-text-muted">— model estimate, not a guarantee</span>
    </p>
  );
}
