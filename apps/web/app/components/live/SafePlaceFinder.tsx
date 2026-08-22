"use client";

import { Ambulance, Bus, Loader2, MapPin, Phone, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { Card, CardHeader } from "@/app/components/ui/Card";
import { fetchFacilitiesNear } from "@/lib/api";
import type { Facility } from "@/lib/types";

const TYPE_META: Record<Facility["type"], { label: string; icon: typeof MapPin }> = {
  police: { label: "Police", icon: ShieldCheck },
  hospital: { label: "Hospital", icon: Ambulance },
  fire_station: { label: "Fire station", icon: Phone },
  pharmacy: { label: "Pharmacy", icon: Phone },
  transit_stop: { label: "Transit", icon: Bus },
  public_place: { label: "Public place", icon: MapPin },
};

interface Props {
  lat: number;
  lon: number;
  label: string;
}

export function SafePlaceFinder({ lat, lon, label }: Props) {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchFacilitiesNear(lat, lon)
      .then((rows) => {
        if (cancelled) return;
        setFacilities(rows);
      })
      .catch(() => {
        if (!cancelled) setError("Facilities are unavailable right now.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [lat, lon]);

  const ranked = [...facilities].sort((a, b) => {
    const order = (t: Facility["type"]) =>
      t === "police" ? 0 : t === "hospital" ? 1 : t === "transit_stop" ? 2 : 3;
    return order(a.type) - order(b.type);
  });

  return (
    <Card className="space-y-2">
      <CardHeader
        title="Safe places nearby"
        subtitle={`Within ~2 km of ${label} — from the live facilities index`}
      />
      {loading ? (
        <p className="flex items-center gap-2 py-2 text-xs text-text-muted">
          <Loader2 className="size-3.5 animate-spin" aria-hidden /> Finding places…
        </p>
      ) : error ? (
        <p className="py-2 text-xs text-danger">{error}</p>
      ) : ranked.length === 0 ? (
        <p className="py-2 text-xs text-text-muted">
          No indexed facilities within ~2 km — the index covers Delhi police stations, hospitals,
          transit stops and more.
        </p>
      ) : (
        <ul className="space-y-1.5">
          {ranked.slice(0, 5).map((f) => {
            const meta = TYPE_META[f.type];
            const Icon = meta.icon;
            return (
              <li
                key={f.id}
                className="flex items-center gap-2 rounded-xl border border-border/60 bg-surface/50 px-3 py-2"
              >
                <Icon className="size-3.5 shrink-0 text-primary" aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-medium text-foreground">{f.name}</p>
                  <p className="text-[11px] text-text-muted">
                    {meta.label} · {f.lat.toFixed(4)}, {f.lon.toFixed(4)}
                  </p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      <p className="text-[11px] text-text-muted">
        "Nearby" is proximity, not a safety claim — a place being close does not mean it is safe.
      </p>
    </Card>
  );
}
