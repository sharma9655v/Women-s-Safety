"use client";

import { motion } from "framer-motion";
import { Clock, MoveRight, ShieldCheck } from "lucide-react";
import { FreshnessBadge } from "@/app/components/safety/FreshnessBadge";
import { formatDistance, formatDuration } from "@/lib/format";
import type { RouteCandidate } from "@/lib/types";

const ROUTE_STYLES = {
  recommended: {
    label: "Recommended",
    badge: "border-success/30 bg-success/12 text-success",
    glow: "#06d6a0",
  },
  alternative: {
    label: "Alternative",
    badge: "border-warning/30 bg-warning/12 text-warning",
    glow: "#ffa726",
  },
  shortest: {
    label: "Shortest",
    badge: "border-danger/30 bg-danger/12 text-danger",
    glow: "#ff4757",
  },
} as const;

export interface RouteCardProps {
  route: RouteCandidate;
  selected: boolean;
  hovered: boolean;
  onSelect: () => void;
  onHover: (hovered: boolean) => void;
}

export function RouteCard({ route, selected, hovered, onSelect, onHover }: RouteCardProps) {
  const style = ROUTE_STYLES[route.label] ?? ROUTE_STYLES.recommended;
  const score = route.safety.value;

  return (
    <motion.button
      type="button"
      onClick={onSelect}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      aria-pressed={selected}
      className={`group w-full cursor-pointer rounded-2xl border bg-surface p-3.5 text-left transition-all duration-300 ${
        selected
          ? "border-primary/40 bg-surface-hover shadow-lg shadow-primary/8"
          : "border-border hover:border-primary/30 hover:bg-surface-hover"
      } ${hovered && !selected ? "shadow-md" : ""}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
            {route.title}
            {route.label === "recommended" ? (
              <ShieldCheck
                className="size-3.5 text-success"
                aria-label="Recommended based on available evidence"
              />
            ) : null}
          </p>
          <p className="mt-0.5 truncate text-xs text-text-muted">{route.via}</p>
        </div>
        <div className="relative shrink-0">
          <div
            className="absolute -inset-2 rounded-full opacity-25 blur-lg"
            style={{
              background: `radial-gradient(circle, ${style.glow}66, transparent 70%)`,
            }}
            aria-hidden
          />
          <span
            className={`relative flex shrink-0 items-center gap-1 rounded-full border px-2.5 py-0.5 text-sm font-bold ${style.badge}`}
          >
            {score}
            <span className="text-[10px] font-medium opacity-70">/100</span>
          </span>
        </div>
      </div>

      <div className="mt-2 flex items-center gap-3 text-xs text-text-secondary">
        <span className="flex items-center gap-1">
          <Clock className="size-3.5" aria-hidden />
          {formatDuration(route.duration_s)}
        </span>
        <span className="flex items-center gap-1">
          <MoveRight className="size-3.5" aria-hidden />
          {formatDistance(route.distance_m)}
        </span>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <FreshnessBadge tier={route.freshness.tier} />
        <span className="text-[10px] text-text-muted">Confidence: {route.safety.confidence}</span>
        {route.uncertainty !== undefined ? (
          <span className="text-[10px] text-text-muted">
            Uncertainty: {Math.round(route.uncertainty * 100)}%
          </span>
        ) : null}
      </div>

      {route.label === "recommended" ? (
        <p className="mt-2 border-t border-border pt-2 text-[10px] text-text-muted">
          Recommended based on available evidence — not a safety guarantee.
        </p>
      ) : null}
    </motion.button>
  );
}
