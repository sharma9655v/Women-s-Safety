"use client";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { formatDuration, formatDistance, riskBandLabel, riskBandStyle, FRESHNESS_STYLE, freshnessFromAge } from "@/lib/format";
import { Shield, Clock, MapPin, AlertTriangle, Check, ChevronRight, ChevronLeft } from "lucide-react";
import { RouteCandidate } from "@/lib/types";

interface RouteCardProps { route: RouteCandidate; index: number; selected: boolean; onSelect: () => void; onViewDetails?: () => void; }

export function RouteCard({ route, index, selected, onSelect, onViewDetails }: RouteCardProps) {
  const freshness = freshnessFromAge(route.freshness?.tier === "unknown" ? null : (route.freshness?.updated_at ? (Date.now() - new Date(route.freshness.updated_at).getTime()) / 3600_000 : null));
  const riskColor = riskBandStyle(route.safety.band);
  return (
    <Card variant={selected ? "glass-strong" : "glass"} className={`relative flex flex-col ${selected ? "border-primary/40 ring-2 ring-primary/20" : ""} group`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl font-display font-bold text-primary/80">{index + 1}</span>
          <div>
            <div className="flex items-center gap-1.5 text-sm">
              <Badge variant={route.label === "recommended" ? "success" : route.label === "alternative" ? "info" : "warn"}>{route.label}</Badge>
              <span className="font-medium">{route.title}</span>
            </div>
            <p className="text-xs text-text-mid mt-0.5">{route.via}</p>
          </div>
        </div>
        <Button variant={selected ? "primary" : "ghost"} size="sm" onClick={onSelect} className="shrink-0">
          {selected ? <Check size={16} /> : <ChevronRight size={16} />}
        </Button>
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <div className="glass p-3 rounded-xl text-center"><Clock size={18} className="mx-auto text-accent" /><p className="text-xs text-text-low">Duration</p><p className="font-semibold">{formatDuration(route.duration_s)}</p></div>
        <div className="glass p-3 rounded-xl text-center"><MapPin size={18} className="mx-auto text-accent" /><p className="text-xs text-text-low">Distance</p><p className="font-semibold">{formatDistance(route.distance_m)}</p></div>
        <div className="glass p-3 rounded-xl text-center"><Shield size={18} className={`mx-auto ${riskColor}`} /><p className="text-xs text-text-low">Safety</p><p className={`font-semibold ${riskColor}`}>{riskBandLabel(route.safety.band)}</p></div>
      </div>
      <div className="mt-3 flex items-center gap-2 flex-wrap text-xs">
        <Badge className={FRESHNESS_STYLE[freshness.tier]}>{freshness.label}</Badge>
        {route.warnings?.map((w, i) => <Badge key={i} variant="danger"><AlertTriangle size={10} /> {w}</Badge>)}
        {route.reasons?.map((r, i) => <Badge key={i} variant="info">{r}</Badge>)}
      </div>
      {onViewDetails && <Button variant="ghost" size="sm" onClick={onViewDetails} className="mt-3 w-full justify-center text-text-mid hover:text-primary">View segment evidence <ChevronRight size={14} /></Button>}
    </Card>
  );
}