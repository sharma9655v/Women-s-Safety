"use client";
import { ReactNode, useState } from "react";

export function Tabs({ defaultValue, items, render, children, className = "", onChange }: { defaultValue: string; items: { value: string; label: string }[]; render?: (value: string) => ReactNode; children?: ReactNode | ((value: string) => ReactNode); className?: string; onChange?: (v: string) => void }) {
  const [value, setValue] = useState(defaultValue);
  const handleChange = (v: string) => { setValue(v); onChange?.(v); };
  const content = typeof children === "function" ? children(value) : render?.(value) ?? (typeof children === "object" ? children : null);
  return (
    <div className={className}>
      <div className="flex gap-1 bg-surface-elevated/50 p-1 rounded-xl border border-line">
        {items.map((item) => (
          <button key={item.value} onClick={() => handleChange(item.value)} className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${value === item.value ? "bg-primary text-bg shadow-primary-glow" : "text-text-mid hover:text-text-hi hover:bg-white/5"}`}>
            {item.label}
          </button>
        ))}
      </div>
      <div className="mt-4 animate-in">{content}</div>
    </div>
  );
}