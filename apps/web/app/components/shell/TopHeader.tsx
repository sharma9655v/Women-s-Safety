"use client";

import { BadgeCheck, Bell, ChevronDown, MapPin, Search, SearchX } from "lucide-react";
import { useMemo, useState } from "react";
import { ThemeToggle } from "@/app/components/theme/ThemeToggle";
import { Avatar } from "@/app/components/ui/Avatar";
import { Dropdown } from "@/app/components/ui/Dropdown";
import { IconButton } from "@/app/components/ui/IconButton";

const LOCATIONS = [
  { id: "delhi", label: "Delhi, India", hint: "Current region" },
  { id: "noida", label: "Noida, India", hint: "Nearby region" },
  { id: "gurugram", label: "Gurugram, India", hint: "Nearby region" },
];

const SUGGESTIONS = [
  { id: "cp", label: "Connaught Place", hint: "Market & metro hub" },
  { id: "ig", label: "India Gate", hint: "Landmark" },
  { id: "ak", label: "Akshardham, Delhi", hint: "Temple complex" },
  { id: "ito", label: "ITO Crossing", hint: "Business district" },
  { id: "ln", label: "Lajpat Nagar", hint: "Market area" },
];

export function TopHeader() {
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];
    return SUGGESTIONS.filter(
      (s) => s.label.toLowerCase().includes(q) || s.hint.toLowerCase().includes(q),
    ).slice(0, 5);
  }, [query]);

  return (
    <header className="glass relative z-20 flex h-14 shrink-0 items-center gap-3 border-x-0 border-t-0 px-4">
      {/* Location selector */}
      <Dropdown
        value="delhi"
        options={LOCATIONS}
        onChange={() => {}}
        ariaLabel="Select location"
        trigger={
          <span className="flex items-center gap-1.5">
            <MapPin className="size-4 text-primary" aria-hidden />
            <span className="text-sm font-medium">Delhi, India</span>
          </span>
        }
      />

      <div className="mx-1 h-6 w-px bg-border" />

      {/* Search */}
      <div className="relative min-w-0 max-w-xl flex-1">
        <Search
          className="pointer-events-none absolute top-1/2 left-3 z-10 size-4 -translate-y-1/2 text-text-muted"
          aria-hidden
        />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 150)}
          placeholder="Search for a place, area or address..."
          aria-label="Search for a place, area or address"
          className="h-9 w-full rounded-full border border-border bg-surface pr-14 pl-9 text-sm text-foreground transition-all duration-300 placeholder:text-text-muted focus:border-primary/40 focus:bg-surface-hover focus:shadow-md focus:outline-none"
        />
        <kbd
          aria-hidden
          className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 rounded border border-border bg-surface-elevated px-1.5 py-0.5 text-[10px] text-text-muted"
        >
          ⌘K
        </kbd>
        {focused && query.trim().length >= 2 ? (
          <ul className="glass-strong absolute top-full left-0 z-50 mt-1 w-full overflow-hidden rounded-xl shadow-2xl">
            {matches.length === 0 ? (
              <li className="flex items-center gap-2 px-3 py-3 text-sm text-text-muted">
                <SearchX className="size-4" aria-hidden /> No results for &ldquo;
                {query}&rdquo;
              </li>
            ) : (
              matches.map((m) => (
                <li key={m.id}>
                  <button
                    type="button"
                    className="flex w-full cursor-pointer items-center gap-2.5 px-3 py-2.5 text-left text-sm text-foreground transition-colors duration-100 hover:bg-surface-hover"
                    onMouseDown={(e) => {
                      e.preventDefault();
                      setQuery(m.label);
                      setFocused(false);
                    }}
                  >
                    <MapPin className="size-3.5 text-primary" aria-hidden />
                    <span className="flex-1">{m.label}</span>
                    <span className="text-xs text-text-muted">{m.hint}</span>
                  </button>
                </li>
              ))
            )}
          </ul>
        ) : null}
      </div>

      <div className="flex-1" />

      {/* Notifications */}
      <IconButton label="Notifications (4 new)">
        <span className="relative">
          <Bell className="size-4" aria-hidden />
          <span className="absolute -top-1.5 -right-1.5 flex size-3.5 items-center justify-center rounded-full bg-emergency text-[8px] font-bold text-white">
            4
          </span>
        </span>
      </IconButton>

      {/* Theme */}
      <ThemeToggle />

      {/* Profile */}
      <button
        type="button"
        className="flex cursor-pointer items-center gap-2.5 rounded-xl px-2 py-1 transition-colors duration-150 hover:bg-surface-hover"
        aria-label="Profile: Ananya Sharma, Verified User"
      >
        <Avatar initials="AS" label="Ananya Sharma" index={2} />
        <span className="hidden text-left lg:block">
          <span className="flex items-center gap-1 text-sm font-medium text-foreground">
            Ananya
            <BadgeCheck className="size-3.5 text-info" aria-label="Verified User" />
          </span>
          <span className="block text-[10px] text-text-muted">Verified User</span>
        </span>
        <ChevronDown className="hidden size-3.5 text-text-muted lg:block" aria-hidden />
      </button>
    </header>
  );
}
