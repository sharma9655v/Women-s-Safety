"use client";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { AuroraScene } from "@/components/three/AuroraScene";
import { Shield, MapPin, Route, AlertTriangle, Users, Phone, Sparkles, ArrowRight, Loader2 } from "lucide-react";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { formatDistance, formatDuration } from "@/lib/format";

const QUICK_ACTIONS = [
  { href: "/plan", label: "Plan a Route", desc: "Safety-first routing with live risk", icon: Route, colorClass: "text-primary" },
  { href: "/sos", label: "Emergency SOS", desc: "One-tap alert with guardian escalation", icon: AlertTriangle, colorClass: "text-emergency" },
  { href: "/live", label: "Live Dashboard", desc: "Heatmap, incidents & safe places", icon: MapPin, colorClass: "text-accent" },
  { href: "/community", label: "Community Feed", desc: "Verified local safety updates", icon: Users, colorClass: "text-warn" },
];

export default function LandingContent() {
  const { data: areas } = useQuery("areas", () => api.areas(), { revalidateMs: 60_000 });
  const { data: health } = useQuery("cv-health", () => api.cvHealth(), { revalidateMs: 120_000 });

  return (
    <div className="relative min-h-screen flex flex-col">
      <section className="relative flex-1 flex items-center justify-center overflow-hidden">
        <AuroraScene />
        <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-20 sm:py-32">
          <div className="text-center animate-in">
            <div className="inline-flex items-center gap-2 glass px-4 py-1.5 rounded-full text-sm mb-6">
              <span className="size-2 rounded-full bg-safe animate-pulse" />
              <span className="text-text-mid">Live backend connected</span>
            </div>
            <h1 className="font-display text-5xl sm:text-7xl font-bold tracking-tight text-text-hi mb-6">
              Safety-Aware Navigation
              <br />
              <span className="gradient-aurora bg-clip-text text-transparent">That Never Guarantees Safety</span>
            </h1>
            <p className="mx-auto max-w-2xl text-lg sm:text-xl text-text-mid mb-10">
              Plan routes with real-time risk evidence. Share journeys with guardians.
              Trigger SOS with a long press. All risk estimates are probabilistic — never absolute.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/plan"><Button size="lg" className="w-full sm:w-auto"><Sparkles size={20} /> Plan Safer Route</Button></Link>
              <Link href="/sos"><Button size="lg" variant="danger" className="w-full sm:w-auto"><Shield size={20} /> Emergency SOS</Button></Link>
            </div>
          </div>
        </div>
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce" aria-hidden><ArrowRight size={28} className="text-text-low" /></div>
      </section>

      <section className="py-16 sm:py-24 bg-surface/30 border-y border-line">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="font-display text-3xl font-semibold mb-2">Live City Pulse</h2>
            <p className="text-text-mid max-w-2xl mx-auto">Real-time safety data from your city — updated continuously</p>
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard icon={<Shield size={24} className="text-safe" />} label="Areas Scored" value={areas?.length ?? "—"} desc="Neighbourhood safety bands" />
            <StatCard icon={<AlertTriangle size={24} className="text-warn" />} label="Active Alerts" value={health?.models.length ?? "—"} desc="Community verified incidents" />
            <StatCard icon={<Route size={24} className="text-accent" />} label="Routes Today" value="—" desc="Safety-first paths computed" />
            <StatCard icon={<Users size={24} className="text-primary" />} label="Community Posts" value="—" desc="Verified local updates" />
          </div>
        </div>
      </section>

      <section className="py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="font-display text-3xl font-semibold mb-2">Quick Actions</h2>
            <p className="text-text-mid max-w-2xl mx-auto">Everything you need, one tap away</p>
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {QUICK_ACTIONS.map((action) => (
              <Link key={action.href} href={action.href} className="glass group p-6 rounded-2xl hover:border-primary/30 transition-colors">
                <div className="flex items-center justify-center size-12 rounded-xl bg-primary/10 mb-4 text-primary"><action.icon size={24} /></div>
                <h3 className="font-display font-semibold mb-1">{action.label}</h3>
                <p className="text-sm text-text-mid mb-4">{action.desc}</p>
                <span className="inline-flex items-center gap-1 text-sm font-medium text-primary group-hover:gap-2 transition">Open <ArrowRight size={14} /></span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <footer className="py-8 border-t border-line">
        <div className="mx-auto max-w-7xl px-4 text-center text-sm text-text-low">
          <p>This platform provides <strong>risk estimates</strong> based on available evidence. It <strong>never guarantees safety</strong>. Always use your judgement and local knowledge.</p>
          <p className="mt-2">Map data © OpenStreetMap contributors. Basemap © CARTO.</p>
        </div>
      </footer>
    </div>
  );
}

function StatCard({ icon, label, value, desc }: { icon: React.ReactNode; label: string; value: string | number; desc: string }) {
  return (
    <Card variant="glass" className="text-center">
      <div className="mb-3">{icon}</div>
      <p className="font-display text-3xl font-bold text-text-hi">{value}</p>
      <p className="text-sm font-medium text-text-mid">{label}</p>
      <p className="text-xs text-text-low mt-1">{desc}</p>
    </Card>
  );
}