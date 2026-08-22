import { forwardRef, InputHTMLAttributes } from "react";

export const Switch = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & { label?: string }>(
  ({ className = "", label, id, ...props }, ref) => {
    const uid = id ?? `switch-${Math.random().toString(36).slice(2)}`;
    return (
      <label className={`inline-flex items-center gap-3 cursor-pointer ${className}`}>
        <input type="checkbox" ref={ref} id={uid} className="sr-only peer" {...props} />
        <div className="relative w-11 h-6 bg-surface-elevated rounded-full peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary/40
          peer-checked:bg-primary peer-checked:shadow-primary-glow transition-colors">
          <span className="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-md transition-transform peer-checked:translate-x-5" />
        </div>
        {label && <span className="text-sm text-text-hi">{label}</span>}
      </label>
    );
  },
);
Switch.displayName = "Switch";