import { InputHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = "", error, label, ...props }, ref) => (
    <div className="w-full">
      {label && <label className="block text-sm font-medium text-text-mid mb-1.5">{label}</label>}
      <input
        ref={ref}
        className={`w-full px-4 py-2.5 bg-surface-elevated/50 border rounded-xl text-text-hi placeholder:text-text-low
          focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary
          ${error ? "border-danger focus:ring-danger/40" : "border-line"}
          ${className}`}
        {...props}
      />
      {error && <p className="mt-1.5 text-sm text-danger">{error}</p>}
    </div>
  ),
);
Input.displayName = "Input";