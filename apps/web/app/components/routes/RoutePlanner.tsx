"use client";

import { AlertCircle, Clock, MapPin, Navigation } from "lucide-react";
import { useState } from "react";
import { Button } from "@/app/components/ui/Button";
import { Card } from "@/app/components/ui/Card";
import { TransportSelector } from "./TransportSelector";

export const PLACE_SUGGESTIONS = [
  { label: "Connaught Place", lat: 28.6315, lon: 77.2167 },
  { label: "India Gate", lat: 28.6129, lon: 77.2295 },
  { label: "Lodhi Garden", lat: 28.5931, lon: 77.2197 },
  { label: "Akshardham", lat: 28.6127, lon: 77.2773 },
  { label: "ITO", lat: 28.6289, lon: 77.2405 },
  { label: "Lajpat Nagar", lat: 28.5677, lon: 77.2433 },
  { label: "Hauz Khas", lat: 28.5494, lon: 77.2001 },
  { label: "Saket", lat: 28.5245, lon: 77.2066 },
  { label: "Dwarka Sec 21", lat: 28.5563, lon: 77.0579 },
  { label: "Rajouri Garden", lat: 28.6481, lon: 77.1212 },
];

export function RoutePlanner({
  onFindRoutes,
  loading,
  error,
}: {
  onFindRoutes: (origin: string, destination: string, mode: string, hourIst?: number) => void;
  loading: boolean;
  error: string | null;
}) {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [mode, setMode] = useState("walking");
  const [simulateNight, setSimulateNight] = useState(false);

  const canSearch = origin.trim().length >= 2 && destination.trim().length >= 2;

  const submit = () => {
    if (canSearch && !loading) {
      onFindRoutes(origin, destination, mode, simulateNight ? 22 : undefined);
    }
  };

  return (
    <Card className="space-y-3">
      <h2 className="flex items-center gap-2 text-sm font-bold text-foreground">
        <Navigation className="size-4 text-primary" aria-hidden />
        Plan a Route
      </h2>

      <div className="space-y-2">
        <div className="relative">
          <MapPin
            className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-success"
            aria-hidden
          />
          <input
            type="text"
            value={origin}
            onChange={(e) => setOrigin(e.target.value)}
            placeholder="Starting point"
            aria-label="Starting point"
            list="origin-suggestions"
            className="h-10 w-full rounded-xl border border-border bg-surface pl-9 pr-3 text-sm text-foreground transition-all duration-200 placeholder:text-text-muted focus:border-primary/40 focus:bg-surface-hover focus:outline-none"
          />
          <datalist id="origin-suggestions">
            {PLACE_SUGGESTIONS.map((p) => (
              <option key={p.label} value={p.label} />
            ))}
          </datalist>
        </div>

        <div className="relative">
          <MapPin
            className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-emergency"
            aria-hidden
          />
          <input
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="Destination"
            aria-label="Destination"
            list="dest-suggestions"
            className="h-10 w-full rounded-xl border border-border bg-surface pl-9 pr-3 text-sm text-foreground transition-all duration-200 placeholder:text-text-muted focus:border-primary/40 focus:bg-surface-hover focus:outline-none"
          />
          <datalist id="dest-suggestions">
            {PLACE_SUGGESTIONS.map((p) => (
              <option key={p.label} value={p.label} />
            ))}
          </datalist>
        </div>
      </div>

      <TransportSelector value={mode} onChange={setMode} />

      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-[11px] text-text-muted">
          <Clock className="size-3" aria-hidden /> Demo: simulate time
        </span>
        <div
          role="radiogroup"
          aria-label="Simulated time"
          className="flex gap-0.5 rounded-full border border-border bg-surface p-0.5"
        >
          {[
            { id: false, label: "Now" },
            { id: true, label: "Night" },
          ].map((option) => (
            <button
              key={option.label}
              type="button"
              aria-pressed={simulateNight === option.id}
              onClick={() => setSimulateNight(option.id)}
              className={`rounded-full px-3 py-1 text-[11px] font-medium transition-colors duration-150 ${
                simulateNight === option.id
                  ? "bg-primary/15 text-primary-hover"
                  : "text-text-muted hover:bg-surface-hover hover:text-foreground"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <Button fullWidth loading={loading} disabled={!canSearch} onClick={submit}>
        <Navigation className="size-4" aria-hidden />
        Find Safe Route
      </Button>

      {error ? (
        <div className="flex items-start gap-2 rounded-xl border border-danger/20 bg-danger/5 p-3 text-xs text-danger">
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
          {error}
        </div>
      ) : null}
    </Card>
  );
}
