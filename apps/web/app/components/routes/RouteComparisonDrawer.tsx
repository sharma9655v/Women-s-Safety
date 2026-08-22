"use client";
import { Drawer } from "@/components/ui/Drawer";
import { RouteCard } from "./RouteCard";
import { RouteCandidate } from "@/lib/types";
import { X, ChevronLeft, ChevronRight } from "lucide-react";

export function RouteCompareDrawer({ open, onClose, routes, selectedIndex, onSelect }: { open: boolean; onClose: () => void; routes: RouteCandidate[]; selectedIndex: number; onSelect: (i: number) => void }) {
  return (
    <Drawer open={open} onClose={onClose} side="right" className="lg:max-w-xl">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-display font-semibold">Route Comparison ({routes.length})</h3>
        </div>
        {routes.map((r, i) => (
          <RouteCard key={r.id} route={r} index={i} selected={i === selectedIndex} onSelect={() => onSelect(i)} />
        ))}
        <div className="pt-4 border-t border-line flex gap-2">
          <button onClick={() => onSelect(Math.max(0, selectedIndex - 1))} disabled={selectedIndex === 0} className="flex-1 px-3 py-2 rounded-xl bg-surface-elevated text-text-hi disabled:opacity-40">← Previous</button>
          <button onClick={() => onSelect(Math.min(routes.length - 1, selectedIndex + 1))} disabled={selectedIndex === routes.length - 1} className="flex-1 px-3 py-2 rounded-xl bg-primary text-bg disabled:opacity-40">Next →</button>
        </div>
      </div>
    </Drawer>
  );
}