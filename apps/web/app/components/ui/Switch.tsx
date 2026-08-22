"use client";

interface SwitchProps {
  checked: boolean;
  onChange: (next: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  id?: string;
}

/** Accessible toggle switch. */
export function Switch({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  id,
}: SwitchProps) {
  const switchId = id ?? `switch-${label?.replace(/\s+/g, "-").toLowerCase() ?? "toggle"}`;
  return (
    <label
      htmlFor={switchId}
      className={`flex items-start justify-between gap-3 py-2.5 ${disabled ? "opacity-50" : "cursor-pointer"}`}
    >
      <span className="min-w-0">
        {label ? (
          <span className="block text-sm font-semibold text-foreground">{label}</span>
        ) : null}
        {description ? (
          <span className="mt-0.5 block text-xs text-text-muted">{description}</span>
        ) : null}
      </span>
      <span
        className={`relative mt-0.5 inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-300 ${
          checked ? "gradient-brand" : "bg-surface-elevated border border-border"
        }`}
      >
        <input
          id={switchId}
          type="checkbox"
          role="switch"
          aria-checked={checked}
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
          className="peer sr-only"
        />
        <span
          aria-hidden
          className={`size-5 rounded-full bg-white shadow-md transition-transform duration-300 ${
            checked ? "translate-x-[22px]" : "translate-x-0.5"
          }`}
        />
      </span>
    </label>
  );
}
