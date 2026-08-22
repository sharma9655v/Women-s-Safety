"use client";
import { useState } from "react";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { PlannerForm } from "@/components/routes/PlannerForm";
import { RouteCard } from "@/components/routes/RouteCard";
import { RouteCompareDrawer } from "@/components/routes/RouteComparisonDrawer";
import { EvidenceDrawer } from "@/components/map/EvidenceDrawer";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Tabs } from "@/components/ui/Tabs";
import { formatDuration, formatDistance, riskBandLabel, riskBandStyle, freshnessFromAge, FRESHNESS_STYLE } from "@/lib/format";
import { Loader2, Shield, Clock, MapPin, AlertTriangle, ChevronLeft, ChevronRight, X, Map, Search, Navigation } from "lucide-react";

export default function PlanPage() {
  const [results, setResults] = useState<import("@/lib/types").RouteCandidate[]>([]);
  const [selected, setSelected] = useState(0);
  const [compareOpen, setCompareOpen] = useState(false);
  const [evidenceOpen, setEvidenceOpen] = useState<{ open: boolean; segmentId: number } | null>(null);
  const [geocoding, setGeocoding] = useState(false);

  const handleResults = (routes: import("@/lib/types").RouteCandidate[]) => {
    setResults(routes);
    setSelected(0);
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col lg:flex-row">
      {/* Left panel - form + results */}
      <div className="lg:w-1/3 h-[calc(100vh-4rem)] overflow-y-auto border-r border-line flex flex-col">
        <div className="p-4 border-b border-line sticky top-0 bg-surface/95 backdrop-blur z-10">
          <h2 className="font-display font-semibold">Plan Route</h2>
        </div>
        <div className="p-4 flex-1 overflow-y-auto">
          <PlannerForm onResults={handleResults} />
          {results.length > 0 && (
            <div className="mt-6 space-y-3">
              <h3 className="font-medium">Routes Found ({results.length})</h3>
              {results.map((r, i) => (
                <RouteCard key={r.id} route={r} index={i} selected={i === selected} onSelect={() => setSelected(i)} onViewDetails={() => setEvidenceOpen({ open: true, segmentId: r.segment_ids?.[0] ?? 0 })} />
              ))}
              {results.length > 1 && (
                <Button variant="outline" className="w-full mt-4" onClick={() => setCompareOpen(true)}>
                  Compare All Routes <Navigation size={16} />
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right panel - map + details */}
      <div className="lg:w-2/3 h-[calc(100vh-4rem)] relative flex flex-col">
        {/* Map placeholder - real implementation would use MapCanvas with route geometries */}
        <div className="h-full lg:h-[calc(100vh-4rem)] glass relative">
          <div className="absolute inset-0 flex items-center justify-center bg-bg/50">
            <div className="text-center p-8">
              <Map size={48} className="mx-auto text-text-low mb-4" />
              <p className="text-text-mid">Route map with risk coloring</p>
              <p className="text-xs text-text-low mt-1">Select a route to visualize</p>
            </div>
          </div>
          {results.length > 0 && selected < results.length && (
            <div className="absolute bottom-4 left-4 right-4 lg:static lg:ml-4 lg:mr-4 lg:mb-4 lg:bottom-auto lg:top-4 lg:w-72">
              <Card variant="glass-strong" className="space-y-3">
                <h4 className="font-semibold">Selected Route</h4>
                <div className="grid gap-2 sm:grid-cols-3 text-center">
                  <div className="glass p-2 rounded-lg"><Clock size={16} className="mx-auto text-accent" /><p className="text-xs text-text-low">Duration</p><p className="font-semibold">{formatDuration(results[selected].duration_s)}</p></div>
                  <div className="glass p-2 rounded-lg"><MapPin size={16} className="mx-auto text-accent" /><p className="text-xs text-text-low">Distance</p><p className="font-semibold">{formatDistance(results[selected].distance_m)}</p></div>
                  <div className="glass p-2 rounded-lg"><Shield size={16} className={`mx-auto ${riskBandStyle(results[selected].safety.band)}`} /><p className="text-xs text-text-low">Safety</p><p className={`font-semibold ${riskBandStyle(results[selected].safety.band)}`}>{riskBandLabel(results[selected].safety.band)}</p></div>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="flex-1">View Evidence</Button>
                  <Button size="sm" className="flex-1">Start Navigation</Button>
                </div>
              </Card>
            </div>
          )}
        </div>
      </div>

      {/* Route Comparison Drawer */}
      <RouteCompareDrawer open={compareOpen} onClose={() => setCompareOpen(false)} routes={results} selectedIndex={selected} onSelect={setSelected} />

      {/* Evidence Drawer */}
      <EvidenceDrawer open={evidenceOpen?.open ?? false} onClose={() => setEvidenceOpen(null)} evidence={evidenceOpen ? null : null} />
    </div>
  );
}