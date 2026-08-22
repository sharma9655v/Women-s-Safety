"use client";

import {
  ChevronDown,
  Cloud,
  Languages,
  MapPin,
  Search,
  SearchX,
  Shield,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { NotificationsBell } from "@/app/components/notifications/NotificationsBell";
import { ThemeToggle } from "@/app/components/theme/ThemeToggle";
import { Dropdown } from "@/app/components/ui/Dropdown";
import { useI18n } from "@/lib/i18n";
import { useDiscreetMode } from "./AppShell";

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
  const { lang, setLang, t } = useI18n();
  const discreet = useDiscreetMode();

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];
    return SUGGESTIONS.filter(
      (s) => s.label.toLowerCase().includes(q) || s.hint.toLowerCase().includes(q),
    ).slice(0, 5);
  }, [query]);

  return (
    <header className="app-top-header glass relative z-20 flex h-14 shrink-0 items-center gap-2 border-x-0 border-t-0 px-3 landscape:max-lg:h-12 sm:px-4">
      {/* Compact identity for portrait and tablet layouts. */}
      <div className="mobile-brand flex min-w-0 items-center gap-2 lg:hidden">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary text-white shadow-md shadow-primary/20">
          {discreet.enabled && !discreet.loading ? (
            <Cloud className="size-5" aria-hidden />
          ) : (
            <Shield className="size-5" aria-hidden />
          )}
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">
            {discreet.enabled && !discreet.loading ? discreet.label : t("appName")}
          </p>
          <p className="flex items-center gap-1 text-[10px] text-text-muted">
            <MapPin className="size-3" aria-hidden /> {t("header.region")}
          </p>
        </div>
      </div>

      <div className="hidden items-center gap-3 lg:flex">
        <Dropdown
          value="delhi"
          options={LOCATIONS}
          onChange={() => {}}
          ariaLabel="Select location"
          trigger={
            <span className="flex items-center gap-1.5">
              <MapPin className="size-4 text-primary" aria-hidden />
              <span className="text-sm font-medium">{t("header.region")}</span>
            </span>
          }
        />
        <div className="mx-1 h-6 w-px bg-border" />
      </div>

      {/* Desktop search. On mobile, route planning owns the primary search action. */}
      <div className="relative hidden min-w-0 max-w-xl flex-1 lg:block">
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
          placeholder={t("header.search")}
          aria-label={t("header.search")}
          className="h-11 w-full rounded-full border border-border bg-surface pr-14 pl-9 text-sm text-foreground transition-all duration-300 placeholder:text-text-muted focus:border-primary/40 focus:bg-surface-hover focus:shadow-md focus:outline-none"
        />
        <kbd
          aria-hidden
          className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 rounded border border-border bg-surface-elevated px-1.5 py-0.5 text-[10px] text-text-muted"
        >
          Cmd K
        </kbd>
        {focused && query.trim().length >= 2 ? (
          <ul className="glass-strong absolute top-full left-0 z-50 mt-1 w-full overflow-hidden rounded-xl shadow-2xl">
            {matches.length === 0 ? (
              <li className="flex items-center gap-2 px-3 py-3 text-sm text-text-muted">
                <SearchX className="size-4" aria-hidden /> No results for &ldquo;{query}&rdquo;
              </li>
            ) : (
              matches.map((m) => (
                <li key={m.id}>
                  <button
                    type="button"
                    className="flex min-h-11 w-full cursor-pointer items-center gap-2.5 px-3 py-2.5 text-left text-sm text-foreground transition-colors duration-100 hover:bg-surface-hover"
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

      <NotificationsBell />

      <div className="hidden items-center gap-2 lg:flex">
        <button
          type="button"
          onClick={() => setLang(lang === "en" ? "hi" : "en")}
          aria-label={lang === "en" ? "Switch language to Hindi" : "Switch language to English"}
          title={lang === "en" ? "Hindi" : "English"}
          className="flex min-h-11 cursor-pointer items-center gap-1 rounded-xl px-2 text-xs font-semibold text-text-secondary transition-colors duration-150 hover:bg-surface-hover hover:text-foreground"
        >
          <Languages className="size-4" aria-hidden />
          {lang === "en" ? "HI" : "EN"}
        </button>
        <ThemeToggle />
      </div>

      {/* Profile is pseudonymous: no fabricated user identity. */}
      <Link
        href="/profile"
        aria-label="Profile: this device, pseudonymous"
        className="flex min-h-11 min-w-11 cursor-pointer items-center justify-center gap-2.5 rounded-xl px-1 transition-colors duration-150 hover:bg-surface-hover lg:min-w-0 lg:justify-start lg:px-2"
      >
        <span className="flex size-9 items-center justify-center rounded-full bg-gradient-to-br from-primary/30 to-accent/20 text-primary ring-2 ring-primary/20">
          <UserRound className="size-4" aria-hidden />
        </span>
        <span className="hidden text-left lg:block">
          <span className="flex items-center gap-1 text-sm font-medium text-foreground">
            This device
          </span>
          <span className="block text-[10px] text-text-muted">Pseudonymous</span>
        </span>
        <ChevronDown className="hidden size-3.5 text-text-muted lg:block" aria-hidden />
      </Link>
    </header>
  );
}
