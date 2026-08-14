import type { FreshnessTier } from "@/lib/types";

const TIER_STYLE: Record<FreshnessTier, string> = {
  fresh: "text-success bg-success/10 border-success/20",
  aging: "text-warning bg-warning/10 border-warning/20",
  stale: "text-danger bg-danger/10 border-danger/20",
  unknown: "text-text-muted bg-surface-hover border-border",
};

const TIER_LABEL: Record<FreshnessTier, string> = {
  fresh: "Fresh",
  aging: "Aging",
  stale: "Stale",
  unknown: "Unknown",
};

export function FreshnessBadge({
  tier,
  className = "",
}: {
  tier: FreshnessTier;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-medium ${TIER_STYLE[tier]} ${className}`}
    >
      {TIER_LABEL[tier]}
    </span>
  );
}
