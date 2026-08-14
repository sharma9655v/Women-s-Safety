export function SkeletonCard({ rows = 3, className = "" }: { rows?: number; className?: string }) {
  const widths = Array.from({ length: Math.max(1, rows) }, (_, i) => Math.max(15, 85 - i * 12));
  return (
    <div className={`rounded-2xl border border-border bg-surface p-4 ${className}`}>
      <div className="skeleton-shimmer mb-3 h-4 w-2/5 rounded-lg" />
      {widths.map((w) => (
        <div key={w} className="skeleton-shimmer mt-2 h-3 rounded-lg" style={{ width: `${w}%` }} />
      ))}
    </div>
  );
}

export function SkeletonLine({ className = "" }: { className?: string }) {
  return <div className={`skeleton-shimmer h-3 rounded-lg ${className}`} />;
}
