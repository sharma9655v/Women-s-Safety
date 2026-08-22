import { ReactNode, useState, useRef, useEffect } from "react";

export function Tooltip({ children, content, position = "top" }: { children: ReactNode; content: string; position?: "top" | "bottom" | "left" | "right" }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const handler = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);
  const positions = { top: "bottom-full left-1/2 -translate-x-1/2 mb-2", bottom: "top-full left-1/2 -translate-x-1/2 mt-2", left: "right-full top-1/2 -translate-y-1/2 mr-2", right: "left-full top-1/2 -translate-y-1/2 ml-2" };
  return (
    <div ref={ref} className="relative inline-block" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}>
      {children}
      {open && <div className={`absolute ${positions[position]} glass-strong px-3 py-1.5 text-xs text-text-mid whitespace-nowrap rounded-lg shadow-glass-lg animate-in z-20`}>{content}</div>}
    </div>
  );
}