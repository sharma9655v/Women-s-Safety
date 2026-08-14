export function Progress({
  value,
  max = 100,
  tone = "primary",
  className = "",
}: {
  value: number;
  max?: number;
  tone?: "primary" | "success" | "warning" | "danger";
  className?: string;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const TONE_BG: Record<string, string> = {
    primary: "bg-primary",
    success: "bg-success",
    warning: "bg-warning",
    danger: "bg-emergency",
  };

  return (
    <div
      className={`h-1.5 w-full overflow-hidden rounded-full bg-surface-hover ${className}`}
      role="progressbar"
      aria-valuenow={value}
      aria-valuemax={max}
    >
      <div
        className={`h-full rounded-full transition-all duration-700 ease-out ${TONE_BG[tone]}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
