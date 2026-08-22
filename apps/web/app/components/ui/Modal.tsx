import { ReactNode, useState, useRef, useEffect } from "react";
import { X } from "lucide-react";

export function Modal({ open, onClose, title, children, className = "" }: { open: boolean; onClose: () => void; title?: string; children: ReactNode; className?: string }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in" onClick={onClose} role="dialog" aria-modal="true">
      <div className={`glass-strong w-full max-w-lg max-h-[90vh] overflow-y-auto ${className}`} onClick={(e) => e.stopPropagation()}>
        {title && (
          <div className="flex items-center justify-between p-4 border-b border-line">
            <h3 className="font-display text-lg font-semibold">{title}</h3>
            <button onClick={onClose} className="p-1 text-text-low hover:text-text-hi rounded-lg hover:bg-white/5" aria-label="Close"><X size={20} /></button>
          </div>
        )}
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}