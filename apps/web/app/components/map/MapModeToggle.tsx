"use client";

import { Box, Layers } from "lucide-react";

export function MapModeToggle({
  mode,
  onChange,
}: {
  mode: "2d" | "3d";
  onChange: (m: "2d" | "3d") => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(mode === "2d" ? "3d" : "2d")}
      aria-label={`Switch to ${mode === "2d" ? "3D" : "2D"} view`}
      className="flex cursor-pointer items-center gap-1.5 rounded-xl border border-border bg-surface/90 px-3 py-2 text-xs font-medium text-text-secondary shadow-md backdrop-blur-md transition-all duration-200 hover:bg-surface-hover hover:text-foreground"
    >
      {mode === "2d" ? (
        <Box className="size-4" aria-hidden />
      ) : (
        <Layers className="size-4" aria-hidden />
      )}
      {mode === "2d" ? "3D" : "2D"}
    </button>
  );
}
