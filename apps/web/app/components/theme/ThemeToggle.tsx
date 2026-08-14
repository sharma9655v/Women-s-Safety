"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { type Theme, useTheme } from "./ThemeProvider";

const OPTIONS: { id: Theme; label: string; icon: typeof Sun }[] = [
  { id: "light", label: "Light", icon: Sun },
  { id: "dark", label: "Dark", icon: Moon },
  { id: "system", label: "System", icon: Monitor },
];

/** Segmented light / dark / system switcher. */
export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <fieldset
      aria-label="Theme"
      className="flex items-center gap-0.5 rounded-full border border-border bg-surface p-0.5"
    >
      {OPTIONS.map(({ id, label, icon: Icon }) => {
        const active = theme === id;
        return (
          <button
            key={id}
            type="button"
            aria-pressed={active}
            aria-label={label}
            title={label}
            onClick={() => setTheme(id)}
            className={`flex h-7 cursor-pointer items-center gap-1 rounded-full px-2.5 text-xs font-medium transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-primary ${
              active
                ? "bg-primary/15 text-primary-hover"
                : "text-text-muted hover:bg-surface-hover hover:text-foreground"
            }`}
          >
            <Icon className="size-3.5" aria-hidden />
            <span className="hidden sm:inline">{label}</span>
          </button>
        );
      })}
    </fieldset>
  );
}
