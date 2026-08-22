import { ReactNode } from "react";
import { X } from "lucide-react";

export function Drawer({ open, onClose, children, side = "right", className = "" }: { open: boolean; onClose: () => void; children: ReactNode; side?: "left" | "right"; className?: string }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex" onClick={onClose} role="dialog" aria-modal="true">
      <div className={`flex-1 bg-black/40 backdrop-blur-sm ${side === "left" ? "order-2" : "order-1"}`} onClick={onClose} />
      <div className={`glass-strong w-full max-w-sm sm:max-w-md lg:max-w-lg flex flex-col h-full shadow-glass-lg ${side === "right" ? "border-l" : "border-r"} border-line ${className}`} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-line">
          <h3 className="font-display font-semibold">Options</h3>
          <button onClick={onClose} className="p-1 text-text-low hover:text-text-hi rounded-lg hover:bg-white/5" aria-label="Close"><X size={20} /></button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
      </div>
    </div>
  );
}