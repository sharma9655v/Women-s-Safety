import { ButtonHTMLAttributes, forwardRef } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "safe" | "outline" | "success";
  size?: "sm" | "md" | "lg" | "icon";
  danger?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = "", children, disabled, variant = "primary", size = "md", danger = false, ...props }, ref) => {
    const base = "inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 disabled:opacity-50 disabled:pointer-events-none";
    const variants = {
      primary: "bg-primary text-bg hover:bg-primary-hover shadow-primary-glow",
      secondary: "bg-surface-elevated text-text-hi hover:bg-surface-elevated/80 border border-line",
      ghost: "text-text-mid hover:text-text-hi hover:bg-white/5",
      danger: "bg-emergency text-bg hover:bg-danger shadow-emergency-glow",
      safe: "bg-safe text-bg hover:bg-safe/90 shadow-safe-glow",
      outline: "border border-line text-text-hi hover:bg-white/5",
      success: "bg-safe text-bg hover:bg-safe/90 shadow-safe-glow",
    };
    const sizes = {
      sm: "px-3 py-1.5 text-sm gap-1.5 rounded-lg",
      md: "px-4 py-2 text-base gap-2 rounded-xl",
      lg: "px-6 py-3 text-lg gap-2.5 rounded-xl",
      icon: "p-2 rounded-xl",
    };
    const variantClass = danger ? variants.danger : variants[variant];
    return (
      <button ref={ref} className={`${base} ${variantClass} ${sizes[size]} ${className}`} disabled={disabled} {...props}>
        {children}
      </button>
    );
  },
);
Button.displayName = "Button";