import { HTMLAttributes, forwardRef } from "react";

export const Progress = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement> & { value: number; max?: number; variant?: "default" | "safe" | "warn" | "danger" }>(
  ({ className = "", value, max = 100, variant = "default", ...props }, ref) => {
    const pct = Math.max(0, Math.min(100, (value / max) * 100));
    const variants = { default: "bg-primary", safe: "bg-safe", warn: "bg-warn", danger: "bg-danger" };
    return (
      <div ref={ref} className={`w-full h-2 bg-surface-elevated rounded-full overflow-hidden ${className}`} {...props}>
        <div className={`${variants[variant]} h-full rounded-full transition-all duration-500 ease-out-expo`} style={{ width: `${pct}%` }} />
      </div>
    );
  },
);
Progress.displayName = "Progress";