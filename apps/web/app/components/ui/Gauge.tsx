"use client";

export function Gauge({
  value,
  max = 100,
  size = 120,
  strokeWidth = 8,
  label,
  sublabel,
  className = "",
}: {
  value: number;
  max?: number;
  size?: number;
  strokeWidth?: number;
  label?: string;
  sublabel?: string;
  className?: string;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.max(0, Math.min(1, value / max));
  const offset = circumference * (1 - pct);

  const color =
    pct >= 0.7
      ? "var(--risk-low)"
      : pct >= 0.45
        ? "var(--risk-moderate)"
        : pct >= 0.25
          ? "var(--risk-elevated)"
          : "var(--risk-limited)";

  return (
    <div className={`relative inline-flex flex-col items-center ${className}`}>
      <svg
        width={size}
        height={size}
        className="-rotate-90"
        aria-label={`Score: ${value} out of ${max}`}
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--surface-hover)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="score-ring-animated"
          style={
            {
              "--circumference": circumference,
              "--score-offset": offset,
            } as React.CSSProperties
          }
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-foreground">{value}</span>
        {label ? <span className="text-[11px] text-text-muted">{label}</span> : null}
      </div>
      {sublabel ? <p className="mt-2 text-xs text-text-muted">{sublabel}</p> : null}
    </div>
  );
}
