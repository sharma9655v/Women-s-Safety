"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, LayoutDashboard, MapPin, AlertTriangle, Users, Phone, Settings, Shield, Route, HelpCircle, LogOut, User, Layers } from "lucide-react";
import { Dropdown } from "@/components/ui/Dropdown";
import { ThemeToggle } from "./ThemeToggle";
import { NotificationsBell } from "./NotificationsBell";

const NAV = [
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

export function TopHeader() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-40 glass border-b border-line">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-display font-semibold text-xl text-text-hi" aria-label="Map for Women Home">
          <span className="size-8 rounded-xl bg-gradient-aurora flex items-center justify-center"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="size-5 text-bg"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/><path d="M12 6v6l4 2"/></svg></span>
          <span className="hidden sm:block">Map for Women</span>
        </Link>
        <nav className="hidden md:flex items-center gap-1">
          {NAV.map((item) => (
            <Link key={item.href} href={item.href} className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${pathname.startsWith(item.href) ? "bg-primary/15 text-primary" : "text-text-mid hover:text-text-hi hover:bg-white/5"}`}>
              <item.icon size={18} className={item.iconClassName} />
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <NotificationsBell />
          <Dropdown
            trigger={<button className="flex items-center gap-2 p-1.5 rounded-lg text-text-mid hover:text-text-hi hover:bg-white/5"><svg className="size-8 rounded-full bg-gradient-aurora" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg><span className="hidden sm:block font-medium">Account</span></button>}
            items={[
              { label: "Settings", onClick: () => {}, icon: <Settings size={16} /> },
              { label: "Sign out", onClick: () => {}, icon: <LogOut size={16} />, danger: true },
            ]}
          />
          <button className="md:hidden p-2 rounded-lg text-text-mid hover:text-text-hi hover:bg-white/5" aria-label="Menu"><svg width={24} height={24} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 12h18M3 6h18M3 18h18"/></svg></button>
        </div>
      </div>
    </header>
  );
}