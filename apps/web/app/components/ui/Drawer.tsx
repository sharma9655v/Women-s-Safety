"use client";

import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import type { ReactNode } from "react";

export function Drawer({
  open,
  onClose,
  children,
  title,
  side = "right",
  className = "",
}: {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  title?: string;
  side?: "left" | "right";
  className?: string;
}) {
  const isRight = side === "right";

  return (
    <AnimatePresence>
      {open ? (
        <div className="fixed inset-0 z-[9999] flex">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={onClose}
            aria-hidden
          />
          <motion.aside
            initial={{ x: isRight ? "100%" : "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: isRight ? "100%" : "-100%" }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            className={`glass-strong relative z-10 flex h-full w-full max-w-md flex-col overflow-y-auto ${
              isRight ? "ml-auto" : ""
            } ${className}`}
          >
            {title ? (
              <div className="flex items-center justify-between border-b border-border p-4">
                <h2 className="text-lg font-bold text-foreground">{title}</h2>
                <button
                  type="button"
                  onClick={onClose}
                  className="flex size-8 cursor-pointer items-center justify-center rounded-lg text-text-muted transition-colors hover:bg-surface-hover hover:text-foreground"
                  aria-label="Close"
                >
                  <X className="size-4" />
                </button>
              </div>
            ) : null}
            <div className="flex-1 p-4">{children}</div>
          </motion.aside>
        </div>
      ) : null}
    </AnimatePresence>
  );
}
