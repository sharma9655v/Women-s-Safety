"use client";

import { Minus, Plus, RotateCcw } from "lucide-react";
import type { MutableRefObject } from "react";
import type { RouteMapApi } from "./MapCanvas";

export function MapControls({
  apiRef,
  mode,
}: {
  apiRef: MutableRefObject<RouteMapApi | null>;
  mode: "2d" | "3d";
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <button
        type="button"
        onClick={() => apiRef.current?.zoomIn()}
        aria-label="Zoom in"
        className="map-control-button flex size-11 cursor-pointer items-center justify-center rounded-xl border border-border bg-surface/90 text-text-secondary shadow-md backdrop-blur-md transition-all duration-200 hover:bg-surface-hover hover:text-foreground"
      >
        <Plus className="size-4" />
      </button>
      <button
        type="button"
        onClick={() => apiRef.current?.zoomOut()}
        aria-label="Zoom out"
        className="map-control-button flex size-11 cursor-pointer items-center justify-center rounded-xl border border-border bg-surface/90 text-text-secondary shadow-md backdrop-blur-md transition-all duration-200 hover:bg-surface-hover hover:text-foreground"
      >
        <Minus className="size-4" />
      </button>
      <button
        type="button"
        onClick={() =>
          mode === "3d" ? apiRef.current?.resetTransform() : apiRef.current?.resetView()
        }
        aria-label="Reset view"
        className="map-control-button flex size-11 cursor-pointer items-center justify-center rounded-xl border border-border bg-surface/90 text-text-secondary shadow-md backdrop-blur-md transition-all duration-200 hover:bg-surface-hover hover:text-foreground"
      >
        <RotateCcw className="size-4" />
      </button>
    </div>
  );
}
