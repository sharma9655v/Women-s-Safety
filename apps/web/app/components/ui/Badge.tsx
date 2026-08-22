import { HTMLAttributes, forwardRef } from "react";

export const Badge = forwardRef<HTMLSpanElement, HTMLAttributes<HTMLSpanElement> & { variant?: "default" | "success" | "warn" | "danger" | "info" }>(
  ({ className = "", children, variant = "default", ...props }, ref) => {
    const variants = {
      default: "bg-surface-elevated text-text-mid border border-line",
      success: "bg-safe/15 text-safe border-safe/30",
      warn: "bg-warn/15 text-warn border-warn/30",
      danger: "bg-danger/15 text-danger border-danger/30",
      info: "bg-accent/15 text-accent border-accent/30",
    };
    return (
      <span ref={ref} className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${variants[variant]} ${className}`} {...props}>
        {children}
      </span>
    );
  },
);
Badge.displayName = "Badge";