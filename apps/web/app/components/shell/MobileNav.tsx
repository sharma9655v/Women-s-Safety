"use client";

import {
  AlertTriangle,
  Bell,
  Map as MapIcon,
  Route as RouteIcon,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { type TKey, useI18n } from "@/lib/i18n";
import { useSos } from "./AppShell";

const TABS: { id: string; icon: typeof MapIcon; label: string; labelKey?: TKey; href: string }[] = [
  { id: "map", icon: MapIcon, labelKey: "nav.map", label: "Map", href: "/live" },
  { id: "routes", icon: RouteIcon, label: "Routes", href: "/live#plan" },
  { id: "alerts", icon: Bell, labelKey: "nav.alerts", label: "Alerts", href: "/alerts" },
  { id: "guardian", icon: ShieldCheck, label: "Guardian", href: "/live#guardian" },
  { id: "profile", icon: UserRound, labelKey: "nav.profile", label: "Profile", href: "/profile" },
];

export function MobileNav() {
  const pathname = usePathname();
  const openSos = useSos();
  const { t } = useI18n();
  const [hash, setHash] = useState("");

  useEffect(() => {
    const syncHash = () => setHash(window.location.hash);
    syncHash();
    window.addEventListener("hashchange", syncHash);
    return () => window.removeEventListener("hashchange", syncHash);
  }, []);

  return (
    <>
      <nav
        aria-label="Mobile navigation"
        className="mobile-nav glass fixed right-0 bottom-0 left-0 z-50 flex items-center justify-around border-x-0 border-b-0 landscape:max-lg:py-1 lg:hidden"
      >
        {TABS.map((tab) => {
          const active =
            tab.id === "map"
              ? pathname === "/live" && hash === ""
              : tab.id === "routes"
                ? pathname === "/live" && hash === "#plan"
                : tab.id === "guardian"
                  ? pathname === "/live" && hash === "#guardian"
                  : pathname.startsWith(tab.href);
          const Icon = tab.icon;
          return (
            <Link
              key={tab.id}
              href={tab.href}
              className={`mobile-nav-item flex min-h-12 min-w-12 flex-col items-center justify-center gap-0.5 rounded-xl px-1 py-1 text-[11px] transition-colors landscape:max-lg:min-h-10 landscape:max-lg:gap-0 ${
                active ? "font-semibold text-primary" : "text-text-muted hover:text-text-secondary"
              }`}
            >
              <Icon className="size-5" aria-hidden />
              {tab.labelKey ? t(tab.labelKey) : tab.label}
            </Link>
          );
        })}
      </nav>
      <button
        type="button"
        onClick={openSos}
        className="mobile-sos-fab fixed z-[60] flex min-h-14 min-w-14 flex-col items-center justify-center gap-0.5 rounded-full bg-emergency text-white shadow-xl shadow-emergency/30 transition-transform duration-200 hover:bg-emergency/90 active:scale-95 landscape:max-lg:min-h-12 landscape:max-lg:min-w-12 landscape:max-lg:bottom-[calc(52px+env(safe-area-inset-bottom))] lg:hidden"
        aria-label="Emergency SOS"
      >
        <AlertTriangle className="size-5" aria-hidden />
        <span className="text-[10px] font-bold tracking-wide">SOS</span>
      </button>
    </>
  );
}
