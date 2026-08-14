"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  Bell,
  Building2,
  Compass,
  FileText,
  Map as MapIcon,
  MessagesSquare,
  Settings,
  Shield,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { EmergencyCard } from "@/app/components/emergency/EmergencyCard";
import { useSos } from "./AppShell";

const NAV = [
  { id: "live", label: "Live Map", icon: MapIcon, href: "/live" },
  { id: "insights", label: "Insights", icon: Compass, href: "/insights" },
  { id: "alerts", label: "Alerts", icon: Bell, href: "/alerts", badge: 4 },
  { id: "report", label: "Report", icon: FileText, href: "/report" },
  {
    id: "community",
    label: "Community",
    icon: MessagesSquare,
    href: "/community",
  },
  {
    id: "civic",
    label: "Civic Ops",
    icon: Building2,
    href: "/civic",
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const openSos = useSos();

  const isActive = (href: string) => {
    if (href === "/live") return pathname === "/live";
    return pathname.startsWith(href);
  };

  return (
    <aside className="glass hidden w-[220px] shrink-0 flex-col border-y-0 border-l-0 md:flex">
      {/* Logo */}
      <div className="flex items-center gap-3 border-b border-border px-4 py-4">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary text-white shadow-lg shadow-primary/25">
          <Shield className="size-5" aria-hidden />
        </span>
        <div className="min-w-0">
          <p className="font-display truncate text-base font-semibold tracking-tight text-foreground">
            Map <span className="text-primary">for Women</span>
          </p>
          <p className="truncate text-[10px] text-text-muted">Safer Routes · Stronger Cities</p>
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
                  className={`relative flex h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors duration-200 ${
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
                  <span className="relative flex-1">{item.label}</span>
                  {"badge" in item && item.badge ? (
                    <span className="relative flex size-5 items-center justify-center rounded-full bg-emergency text-[9px] font-bold text-white">
                      {item.badge}
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
          className="flex h-10 w-full cursor-pointer items-center gap-3 rounded-xl px-3 text-sm font-semibold text-emergency transition-colors duration-150 hover:bg-emergency/8"
        >
          <AlertTriangle className="size-4" aria-hidden />
          Emergency
        </button>

        {/* Bottom links */}
        <ul className="mt-6 space-y-1">
          {[
            {
              id: "profile",
              label: "Profile",
              icon: UserRound,
              href: "/profile",
            },
            {
              id: "settings",
              label: "Settings",
              icon: Settings,
              href: "/settings",
            },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.id}>
                <Link
                  href={item.href}
                  className="flex h-9 items-center gap-3 rounded-xl px-3 text-sm text-text-muted transition-colors duration-150 hover:bg-surface-hover hover:text-foreground"
                >
                  <Icon className="size-4" aria-hidden />
                  {item.label}
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
    </aside>
  );
}
