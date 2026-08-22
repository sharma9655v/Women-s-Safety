"use client";
import { Footprints, Bike, Car, Bus } from "lucide-react";

export function TransportSelector({ value, onChange }: { value: "walking" | "cycling" | "driving"; onChange: (v: "walking" | "cycling" | "driving") => void }) {
  const options = [
    { v: "walking", label: "Walk", icon: Footprints },
    { v: "cycling", label: "Cycle", icon: Bike },
    { v: "driving", label: "Drive", icon: Car },
  ] as const;
  return (
    <div className="flex gap-2" role="radiogroup" aria-label="Transport mode">
      {options.map(({ v, label, icon: Icon }) => (
        <button key={v} onClick={() => onChange(v)} className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${value === v ? "bg-primary text-bg shadow-primary-glow" : "bg-surface-elevated/50 text-text-mid hover:text-text-hi hover:bg-white/5"}`}>
          <Icon size={16} />
          {label}
        </button>
      ))}
    </div>
  );
}