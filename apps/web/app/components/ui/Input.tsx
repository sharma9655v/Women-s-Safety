import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
}

export function Input({ label, hint, className = "", ...rest }: InputProps) {
  return (
    <div>
      {label ? (
        <label htmlFor={rest.id} className="mb-1.5 block text-xs font-medium text-text-secondary">
          {label}
        </label>
      ) : null}
      <input
        className={`h-10 w-full rounded-xl border border-border bg-surface px-3 text-sm text-foreground transition-all duration-200 placeholder:text-text-muted focus:border-primary/50 focus:bg-surface-hover focus:shadow-sm focus:outline-none ${className}`}
        {...rest}
      />
      {hint ? <p className="mt-1 text-right text-[11px] text-text-muted">{hint}</p> : null}
    </div>
  );
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  children: ReactNode;
}

export function Select({ label, children, className = "", ...rest }: SelectProps) {
  return (
    <div>
      {label ? (
        <label htmlFor={rest.id} className="mb-1.5 block text-xs font-medium text-text-secondary">
          {label}
        </label>
      ) : null}
      <select
        className={`h-10 w-full appearance-none rounded-xl border border-border bg-surface px-3 text-sm text-foreground transition-all duration-200 focus:border-primary/50 focus:bg-surface-hover focus:shadow-sm focus:outline-none ${className}`}
        {...rest}
      >
        {children}
      </select>
    </div>
  );
}
