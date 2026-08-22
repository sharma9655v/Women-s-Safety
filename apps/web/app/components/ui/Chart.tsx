"use client";

/** Minimal SVG line-chart. No external charting library. */
export function Chart({
  points,
  width = 400,
  height = 160,
  className = "",
}: {
  points: { x: number; y: number }[];
  width?: number;
  height?: number;
  className?: string;
}) {
  if (points.length < 2) return null;

  const pad = 8;
  const minX = Math.min(...points.map((p) => p.x));
  const maxX = Math.max(...points.map((p) => p.x));
  const minY = Math.min(...points.map((p) => p.y));
  const maxY = Math.max(...points.map((p) => p.y));
  const rangeX = maxX - minX || 1;
  const rangeY = maxY - minY || 1;

  const toSvg = (p: { x: number; y: number }) => ({
    x: pad + ((p.x - minX) / rangeX) * (width - pad * 2),
    y: pad + (1 - (p.y - minY) / rangeY) * (height - pad * 2),
  });

  const mapped = points.map(toSvg);
  const pathD = mapped.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");

  const areaD = `${pathD} L ${mapped[mapped.length - 1].x} ${height - pad} L ${mapped[0].x} ${height - pad} Z`;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={`w-full ${className}`}
      aria-label="Safety score trend chart"
    >
      <defs>
        <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.2" />
          <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaD} fill="url(#chartGrad)" />
      <path
        d={pathD}
        fill="none"
        stroke="var(--primary)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {mapped.map((p) => (
        <circle
          key={p.x}
          cx={p.x}
          cy={p.y}
          r="3"
          fill="var(--surface)"
          stroke="var(--primary)"
          strokeWidth="2"
        />
      ))}
    </svg>
  );
}
