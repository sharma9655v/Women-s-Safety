"use client";
import { useEffect, useState } from "react";
import { Moon, Sun, Monitor } from "lucide-react";
import { Dropdown } from "@/components/ui/Dropdown";

export function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark" | "system">("system");
  useEffect(() => {
    try { const t = localStorage.getItem("mf:theme"); if (t) setTheme(t as any); } catch {}
  }, []);
  const apply = (t: "light" | "dark" | "system") => {
    setTheme(t);
    try { localStorage.setItem("mf:theme", t); } catch {}
    const resolved = t === "system" ? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light") : t;
    document.documentElement.dataset.theme = resolved;
  };
  useEffect(() => { apply(theme); }, [theme]);
  useEffect(() => {
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const handler = () => { if (theme === "system") apply("system"); };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [theme]);
  return (
    <Dropdown
      trigger={<button className="p-1.5 rounded-lg text-text-mid hover:text-text-hi hover:bg-white/5" aria-label="Theme"><Sun size={18} /></button>}
      items={[
        { label: "Light", onClick: () => apply("light"), icon: <Sun size={16} /> },
        { label: "Dark", onClick: () => apply("dark"), icon: <Moon size={16} /> },
        { label: "System", onClick: () => apply("system"), icon: <Monitor size={16} /> },
      ]}
    />
  );
}