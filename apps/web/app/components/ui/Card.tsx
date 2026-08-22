import { HTMLAttributes, forwardRef } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "glass" | "glass-strong" | "elevated" | "emergency";
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className = "", children, variant = "glass", ...props }, ref) => {
    const variants = {
      glass: "glass",
      "glass-strong": "glass-strong",
      elevated: "bg-surface-elevated border border-line",
      emergency: "glass-strong border-emergency/30",
    };
    return (
      <div ref={ref} className={`${variants[variant]} p-4 sm:p-6 ${className}`} {...props}>
        {children}
      </div>
    );
  },
);
Card.displayName = "Card";