"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  Bell,
  BrainCircuit,
  Building2,
  ClipboardCheck,
  Cloud,
  Compass,
  Database,
  FileText,
  Map as MapIcon,
  MapPin,
  MessagesSquare,
  Moon,
  Settings,
  Shield,
  ShieldCheck,
  Sun,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { EmergencyCard } from "@/app/components/emergency/EmergencyCard";
import { fetchAlerts } from "@/lib/api";
import { type TKey, useI18n } from "@/lib/i18n";
import { useDiscreetMode, useSos } from "./AppShell";

const NEUTRAL_ICONS: Record<string, typeof Cloud> = {
  cloud: Cloud,
  sun: Sun,
  moon: Moon,
};

const NAV: { id: string; labelKey: TKey; icon: typeof MapIcon; href: string }[] = [
  { id: "live", labelKey: "nav.map", icon: MapIcon, href: "/live" },
  { id: "insights", labelKey: "nav.insights", icon: Compass, href: "/insights" },
  { id: "alerts", labelKey: "nav.alerts", icon: Bell, href: "/alerts" },
  { id: "report", labelKey: "nav.report", icon: FileText, href: "/report" },
  {
    id: "guardian",
    labelKey: "nav.guardian" as TKey,
    icon: ShieldCheck,
    href: "/live#guardian",
  },
  {
    id: "contacts",
    labelKey: "nav.contacts",
    icon: UserRound,
    href: "/contacts",
  },
  {
    id: "community",
    labelKey: "nav.community",
    icon: MessagesSquare,
    href: "/community",
  },
  {
    id: "civic",
    labelKey: "nav.civic",
    icon: Building2,
    href: "/civic",
  },
  {
    id: "sources",
    labelKey: "nav.sources",
    icon: Database,
    href: "/sources",
  },
  {
    id: "models",
    labelKey: "nav.models",
    icon: BrainCircuit,
    href: "/models",
  },
  {
    id: "admin",
    labelKey: "nav.admin",
    icon: ClipboardCheck,
    href: "/admin",
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const openSos = useSos();
  const discreet = useDiscreetMode();
  const { t } = useI18n();
  const [alertCount, setAlertCount] = useState<number | null>(null);

  // Real alert count from the backend — never a hardcoded badge.
  useEffect(() => {
    let cancelled = false;
    fetchAlerts()
      .then((alerts) => {
        if (!cancelled) setAlertCount(alerts.length);
      })
      .catch(() => {
        if (!cancelled) setAlertCount(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const isActive = (href: string) => {
    if (href === "/live") return pathname === "/live";
    return pathname.startsWith(href);
  };

  return (
    <aside className="glass hidden w-[220px] shrink-0 flex-col border-y-0 border-l-0 lg:flex">
      {/* Logo */}
      <div className="flex items-center gap-3 border-b border-border px-4 py-4">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary text-white shadow-lg shadow-primary/25">
          {discreet.enabled && !discreet.loading ? (
            (() => {
              const NeutralIcon = NEUTRAL_ICONS[discreet.icon] ?? Cloud;
              return <NeutralIcon className="size-5" aria-hidden />;
            })()
          ) : (
            <Shield className="size-5" aria-hidden />
          )}
        </span>
        <div className="min-w-0">
          <p className="font-display truncate text-base font-semibold tracking-tight text-foreground">
            {discreet.enabled && !discreet.loading ? discreet.label : t("appName")}
          </p>
          <p className="truncate text-[10px] text-text-muted">
            {discreet.enabled && !discreet.loading ? "Local services" : t("tagline")}
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav aria-label="Primary" className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-1">
          {NAV.map((item) => {
            const active = isActive(item.href);
            const Icon = item.icon;
            return (
              <li key={item.id}>
                <Link
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`relative flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors duration-200 ${
                    active
                      ? "text-white"
                      : "text-text-secondary hover:bg-surface-hover hover:text-foreground"
                  }`}
                >
                  {active ? (
                    <motion.span
                      layoutId="nav-active"
                      transition={{
                        type: "spring",
                        stiffness: 380,
                        damping: 32,
                      }}
                      className="absolute inset-0 rounded-xl bg-primary shadow-md shadow-primary/20"
                      aria-hidden
                    />
                  ) : null}
                  <Icon className="relative size-4" aria-hidden />
                  <span className="relative flex-1">{t(item.labelKey)}</span>
                  {item.id === "alerts" && alertCount !== null && alertCount > 0 ? (
                    <span className="relative flex size-5 items-center justify-center rounded-full bg-emergency text-[9px] font-bold text-white">
                      {alertCount}
                    </span>
                  ) : null}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Emergency */}
        <div className="my-4 h-px bg-border" />
        <button
          type="button"
          onClick={openSos}
          className="flex min-h-12 w-full cursor-pointer items-center gap-3 rounded-xl px-3 text-sm font-semibold text-emergency transition-colors duration-150 hover:bg-emergency/8"
        >
          <AlertTriangle className="size-4" aria-hidden />
          {t("nav.emergency")}
        </button>

        {/* Bottom links */}
        <ul className="mt-6 space-y-1">
          {[
            {
              id: "profile",
              labelKey: "nav.profile" as TKey,
              icon: UserRound,
              href: "/profile",
            },
            {
              id: "settings",
              labelKey: "nav.settings" as TKey,
              icon: Settings,
              href: "/settings",
            },
            {
              id: "privacy",
              labelKey: "nav.privacy" as TKey,
              icon: Shield,
              href: "/privacy",
            },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.id}>
                <Link
                  href={item.href}
                  className="flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm text-text-muted transition-colors duration-150 hover:bg-surface-hover hover:text-foreground"
                >
                  <Icon className="size-4" aria-hidden />
                  {t(item.labelKey)}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Emergency card */}
      <div className="border-t border-border p-3">
        <EmergencyCard />
      </div>

      {/* Location sharing status */}
      <div className="border-t border-border px-4 py-3">
        <div className="location-sharing-indicator">
          <MapPin className="size-3.5" aria-hidden />
          <span>Location sharing: OFF</span>
        </div>
      </div>
    </aside>
  );
}
