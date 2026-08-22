"use client";

import { Check, Route as RouteIcon } from "lucide-react";
import type { SafetyPreference } from "@/lib/types";

const PROFILES: { id: SafetyPreference; label: string; detail: string }[] = [
  {
    id: "safety",
    label: "Safety Priority",
    detail: "Lower estimated risk first, even if slower.",
  },
  {
    id: "balanced",
    label: "Balanced",
    detail: "Mix of safety, distance and time.",
  },
  {
    id: "time",
    label: "Time Priority",
    detail: "Fastest first; risk still shown.",
  },
];

export function PreferenceSelector({
  value,
  onChange,
}: {
  value: SafetyPreference;
  onChange: (v: SafetyPreference) => void;
}) {
  return (
    <div className="grid grid-cols-3 gap-1.5">
      {PROFILES.map((p) => {
        const active = value === p.id;
        return (
          <button
            key={p.id}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(p.id)}
            className={`min-h-14 cursor-pointer rounded-xl border p-2 text-left transition-colors ${
              active
                ? "border-primary/40 bg-primary/8"
                : "border-border bg-surface hover:border-primary/25"
            }`}
          >
            <span className="flex items-center gap-1 text-[11px] font-semibold text-foreground">
              <RouteIcon className="size-3 text-primary" aria-hidden />
              {p.label}
              {active ? <Check className="size-3 text-primary" aria-hidden /> : null}
            </span>
            <span className="mt-0.5 block text-[9px] leading-tight text-text-muted">
              {p.detail}
            </span>
          </button>
        );
      })}
    </div>
  );
}
