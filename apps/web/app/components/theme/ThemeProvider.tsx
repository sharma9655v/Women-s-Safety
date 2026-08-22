"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";

type Theme = "light" | "dark" | "system";

interface ThemeContextType {
  theme: Theme;
  setTheme: (t: Theme) => void;
  resolvedTheme: "light" | "dark";
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>("system");
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("dark");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    try {
      const stored = localStorage.getItem("mf:theme") as Theme | null;
      if (stored) setTheme(stored);
    } catch {}
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const handler = () => { if (theme === "system") updateResolved(); };
    mq.addEventListener("change", handler);
    updateResolved();
    return () => mq.removeEventListener("change", handler);
  }, [theme]);

  const updateResolved = () => {
    const resolved = theme === "system" ? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light") : theme;
    setResolvedTheme(resolved);
    document.documentElement.dataset.theme = resolved;
  };

  const setThemeWrapper = (t: Theme) => {
    setTheme(t);
    try { localStorage.setItem("mf:theme", t); } catch {}
  };

  if (!mounted) return <>{children}</>;

  return (
    <ThemeContext.Provider value={{ theme, setTheme: setThemeWrapper, resolvedTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}