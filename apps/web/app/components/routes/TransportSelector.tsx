"use client";

import { Bike, Car, Footprints, Train } from "lucide-react";

const MODES = [
  { id: "walking", icon: <Footprints className="size-4" />, label: "Walk" },
  { id: "car", icon: <Car className="size-4" />, label: "Car" },
  { id: "transit", icon: <Train className="size-4" />, label: "Transit" },
  { id: "bicycle", icon: <Bike className="size-4" />, label: "Cycle" },
];

export function TransportSelector({
  value,
  onChange,
}: {
  value: string;
  onChange: (mode: string) => void;
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Transport mode"
      className="flex gap-1 rounded-xl border border-border bg-surface p-1"
    >
      {MODES.map((mode) => (
        <button
          key={mode.id}
          type="button"
          onClick={() => onChange(mode.id)}
          className={`flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium transition-all duration-200 select-none ${
            value === mode.id
              ? "bg-primary text-white shadow-sm"
              : "text-text-muted hover:bg-surface-hover hover:text-foreground"
          }`}
          aria-pressed={value === mode.id}
        >
          {mode.icon}
          <span className="hidden sm:inline">{mode.label}</span>
        </button>
      ))}
    </div>
  );
}
