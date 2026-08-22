"use client";

import { ChevronDown } from "lucide-react";
import { type ReactNode, useEffect, useRef, useState } from "react";

interface DropdownOption {
  id: string;
  label: string;
  hint?: string;
}

export function Dropdown({
  value,
  options,
  onChange,
  ariaLabel,
  trigger,
}: {
  value: string;
  options: DropdownOption[];
  onChange: (id: string) => void;
  ariaLabel: string;
  trigger?: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-label={ariaLabel}
        aria-expanded={open}
        className="flex cursor-pointer items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm text-foreground transition-colors duration-150 hover:bg-surface-hover"
      >
        {trigger ?? <span>{options.find((o) => o.id === value)?.label ?? value}</span>}
        <ChevronDown
          className={`size-3.5 text-text-muted transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          aria-hidden
        />
      </button>
      {open ? (
        <ul className="glass-strong absolute top-full left-0 z-50 mt-1 min-w-[180px] overflow-hidden rounded-xl py-1 shadow-2xl">
          {options.map((opt) => (
            <li key={opt.id}>
              <button
                type="button"
                onClick={() => {
                  onChange(opt.id);
                  setOpen(false);
                }}
                className={`flex w-full cursor-pointer items-center gap-2 px-3 py-2 text-left text-sm transition-colors duration-100 hover:bg-surface-hover ${
                  opt.id === value ? "text-primary font-medium" : "text-foreground"
                }`}
              >
                <span className="flex-1">{opt.label}</span>
                {opt.hint ? <span className="text-xs text-text-muted">{opt.hint}</span> : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
