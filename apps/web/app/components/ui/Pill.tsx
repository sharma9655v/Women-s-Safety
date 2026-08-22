"use client";

import type { ReactNode } from "react";

export function Pill({
  children,
  active = false,
  onClick,
  className = "",
}: {
  children: ReactNode;
  active?: boolean;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex cursor-pointer items-center rounded-full border px-3 py-1 text-xs font-medium capitalize transition-all duration-200 select-none ${
        active
          ? "border-primary/40 bg-primary/12 text-primary shadow-sm"
          : "border-border bg-surface text-text-muted hover:border-border-glow hover:bg-surface-hover hover:text-text-secondary"
      } ${className}`}
    >
      {children}
    </button>
  );
}
