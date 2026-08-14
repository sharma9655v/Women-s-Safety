"use client";

import { AlertTriangle, Bell, Compass, FileText, Map as MapIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSos } from "./AppShell";

const TABS = [
  { id: "live", icon: MapIcon, label: "Map", href: "/live" },
  { id: "insights", icon: Compass, label: "Insights", href: "/insights" },
  { id: "sos", icon: AlertTriangle, label: "SOS", href: "#sos" },
  { id: "alerts", icon: Bell, label: "Alerts", href: "/alerts" },
  { id: "report", icon: FileText, label: "Report", href: "/report" },
];

export function MobileNav() {
  const pathname = usePathname();
  const openSos = useSos();

  return (
    <nav
      aria-label="Mobile navigation"
      className="glass fixed right-0 bottom-0 left-0 z-50 flex h-16 items-center justify-around border-x-0 border-b-0 md:hidden"
    >
      {TABS.map((tab) => {
        if (tab.id === "sos") {
          return (
            <button
              key="sos"
              type="button"
              onClick={openSos}
              className="flex flex-col items-center gap-0.5 text-emergency"
              aria-label="Emergency SOS"
            >
              <span className="flex size-10 items-center justify-center rounded-full bg-emergency text-white shadow-lg animate-ring-pulse">
                <AlertTriangle className="size-5" />
              </span>
            </button>
          );
        }

        const active = pathname.startsWith(tab.href);
        const Icon = tab.icon;
        return (
          <Link
            key={tab.id}
            href={tab.href}
            className={`flex flex-col items-center gap-0.5 px-3 py-1 text-[10px] transition-colors ${
              active ? "font-semibold text-primary" : "text-text-muted hover:text-text-secondary"
            }`}
          >
            <Icon className="size-5" aria-hidden />
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
