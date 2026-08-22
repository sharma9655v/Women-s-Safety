"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, MapPin, AlertTriangle, Users, Phone, Settings, Shield, Route, HelpCircle, User, Layers } from "lucide-react";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  iconClassName?: string;
}

const NAV: readonly NavItem[] = [
  { href: "/live", label: "Live", icon: LayoutDashboard, iconClassName: "" },
  { href: "/plan", label: "Plan", icon: Route, iconClassName: "" },
  { href: "/sos", label: "SOS", icon: AlertTriangle, iconClassName: "text-emergency" },
  { href: "/alerts", label: "Alerts", icon: MapPin, iconClassName: "" },
  { href: "/community", label: "Community", icon: Users, iconClassName: "" },
  { href: "/contacts", label: "Contacts", icon: Phone, iconClassName: "" },
  { href: "/report", label: "Report", icon: Shield, iconClassName: "" },
  { href: "/profile", label: "Profile", icon: User, iconClassName: "" },
  { href: "/privacy", label: "Privacy", icon: Layers, iconClassName: "" },
  { href: "/admin", label: "Admin", icon: Settings, iconClassName: "" },
  { href: "/models", label: "Models", icon: HelpCircle, iconClassName: "" },
] as const;

export function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  return (
    <>
      <button onClick={() => setOpen(true)} className="md:hidden p-2 rounded-lg text-text-mid hover:text-text-hi hover:bg-white/5" aria-label="Menu" aria-expanded={open}>
        <svg width={24} height={24} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
      </button>
      {open && (
        <div className="fixed inset-0 z-50 md:hidden" onClick={() => setOpen(false)}>
          <div className="absolute inset-y-0 right-0 w-72 glass-strong border-l border-line animate-in" onClick={(e) => e.stopPropagation()}>
            <div className="p-4 border-b border-line flex items-center justify-between">
              <span className="font-display font-semibold">Menu</span>
              <button onClick={() => setOpen(false)} className="p-1 rounded-lg text-text-low hover:text-text-hi hover:bg-white/5" aria-label="Close"><svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg></button>
            </div>
            <nav className="flex-1 overflow-y-auto p-3 space-y-1">
              {NAV.map((item) => (
                <Link key={item.href} href={item.href} onClick={() => setOpen(false)} className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${pathname.startsWith(item.href) ? "bg-primary/15 text-primary" : "text-text-mid hover:text-text-hi hover:bg-white/5"}`}>
                  <item.icon size={20} className={item.iconClassName} />
                  <span>{item.label}</span>
                </Link>
              ))}
            </nav>
            <div className="p-4 border-t border-line text-xs text-text-low text-center">Safety estimates — never a guarantee.</div>
          </div>
        </div>
      )}
    </>
  );
}