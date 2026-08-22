import { useState, useRef, useEffect } from "react";
import { ChevronDown } from "lucide-react";

export function Dropdown({
  trigger,
  items,
  align = "end",
}: {
  trigger: React.ReactNode;
  items: { label: string; onClick: () => void; icon?: React.ReactNode; danger?: boolean }[];
  align?: "start" | "end";
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative inline-block">
      <div onClick={() => setOpen(!open)} className="flex items-center gap-1">{trigger} <ChevronDown size={16} className={open ? "rotate-180" : ""} /></div>
      {open && (
        <div className={`absolute z-20 mt-2 min-w-[180px] glass-strong rounded-xl py-1.5 shadow-glass-lg ${align === "end" ? "right-0" : "left-0"}`}>
          {items.map((item, i) => (
            <button key={i} onClick={() => { item.onClick(); setOpen(false); }} className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-text-hi hover:bg-white/5 ${item.danger ? "text-danger" : ""}`}>
              {item.icon && <span className="shrink-0">{item.icon}</span>}
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}