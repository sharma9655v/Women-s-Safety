"use client";

import { AlertCircle, Clock, Crosshair, Loader2, MapPin, Mic, Navigation, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/app/components/ui/Button";
import { Card } from "@/app/components/ui/Card";
import { fetchGeocode } from "@/lib/api";
import type { GeocodeResult } from "@/lib/types";
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

interface Coords {
  lat: number;
  lon: number;
}

interface SpeechRecognitionEvent {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
}

interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((e: SpeechRecognitionEvent) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

function speechRecognitionCtor(): (new () => SpeechRecognitionLike) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: new () => SpeechRecognitionLike;
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function RoutePlanner({
  onFindRoutes,
  loading,
  error,
}: {
  onFindRoutes: (
    origin: string,
    destination: string,
    mode: string,
    hourIst?: number,
    originCoords?: Coords,
    destCoords?: Coords,
  ) => void;
  loading: boolean;
  error: string | null;
}) {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [mode, setMode] = useState("walking");
  const [simulateNight, setSimulateNight] = useState(false);
  const [originCoords, setOriginCoords] = useState<Coords | null>(null);
  const [destCoords, setDestCoords] = useState<Coords | null>(null);
  const [locating, setLocating] = useState(false);
  const [listenLang, setListenLang] = useState<"hi-IN" | "en-IN">("hi-IN");
  const [listening, setListening] = useState(false);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [geoResults, setGeoResults] = useState<{
    origin: GeocodeResult[];
    destination: GeocodeResult[];
  }>({ origin: [], destination: [] });

  // Debounced geocode lookup for both fields. Offline (or API unreachable)
  // it silently falls back to the static PLACE_SUGGESTIONS — the datalist
  // always includes them, so the planner keeps working air-gapped.
  useEffect(() => {
    const timer = setTimeout(() => {
      if (origin.trim().length >= 2 && navigator.onLine) {
        fetchGeocode(origin)
          .then((results) => setGeoResults((prev) => ({ ...prev, origin: results })))
          .catch(() => {});
      } else {
        setGeoResults((prev) => ({ ...prev, origin: [] }));
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [origin]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (destination.trim().length >= 2 && navigator.onLine) {
        fetchGeocode(destination)
          .then((results) => setGeoResults((prev) => ({ ...prev, destination: results })))
          .catch(() => {});
      } else {
        setGeoResults((prev) => ({ ...prev, destination: [] }));
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [destination]);

  const originOptions = useMemo(() => {
    const known = new Map<string, { label: string; lat: number; lon: number }>();
    for (const p of PLACE_SUGGESTIONS) known.set(p.label.toLowerCase(), p);
    for (const r of geoResults.origin)
      known.set(r.name.toLowerCase(), { label: r.name, lat: r.lat, lon: r.lon });
    return Array.from(known.values());
  }, [geoResults.origin]);

  const destOptions = useMemo(() => {
    const known = new Map<string, { label: string; lat: number; lon: number }>();
    for (const p of PLACE_SUGGESTIONS) known.set(p.label.toLowerCase(), p);
    for (const r of geoResults.destination)
      known.set(r.name.toLowerCase(), { label: r.name, lat: r.lat, lon: r.lon });
    return Array.from(known.values());
  }, [geoResults.destination]);

  const applySuggestion = (value: string, target: "origin" | "destination") => {
    const pool = target === "origin" ? originOptions : destOptions;
    const hit = pool.find((p) => p.label.toLowerCase() === value.trim().toLowerCase());
    if (hit) {
      const c = { lat: hit.lat, lon: hit.lon };
      if (target === "origin") setOriginCoords(c);
      else setDestCoords(c);
    }
  };

  const canSearch = origin.trim().length >= 2 && destination.trim().length >= 2;

  const submit = () => {
    if (canSearch && !loading) {
      onFindRoutes(
        origin,
        destination,
        mode,
        simulateNight ? 22 : undefined,
        originCoords ?? undefined,
        destCoords ?? undefined,
      );
    }
  };

  const useMyLocation = () => {
    if (!("geolocation" in navigator)) {
      setVoiceError("Location sharing is not supported by this browser.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const c = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        setOrigin(`${c.lat.toFixed(4)}, ${c.lon.toFixed(4)}`);
        setOriginCoords(c);
        setLocating(false);
      },
      () => {
        setLocating(false);
        setVoiceError("Could not determine your location. Type it instead.");
      },
      { enableHighAccuracy: true, timeout: 8000 },
    );
  };

  const listen = (target: "origin" | "destination") => {
    if (!navigator.onLine) {
      setVoiceError("Voice input needs an internet connection — type the place name instead.");
      return;
    }
    const Ctor = speechRecognitionCtor();
    if (!Ctor) {
      setVoiceError("Voice input needs Chrome or Edge.");
      return;
    }
    setVoiceError(null);
    const rec = new Ctor();
    rec.lang = listenLang;
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (e) => {
      const transcript = e.results[0]?.[0]?.transcript?.trim();
      if (transcript) {
        if (target === "origin") {
          setOrigin(transcript);
          setOriginCoords(null);
        } else {
          setDestination(transcript);
          setDestCoords(null);
        }
      }
    };
    rec.onerror = (e) => {
      setListening(false);
      setVoiceError(
        e.error === "not-allowed"
          ? "Microphone permission was denied."
          : e.error === "network" || e.error === "service-not-allowed"
            ? "Voice input needs an internet connection — type the place name instead."
            : "Voice input failed. Try again.",
      );
    };
    rec.onend = () => setListening(false);
    setListening(true);
    rec.start();
  };

  const clearOrigin = () => {
    setOrigin("");
    setOriginCoords(null);
  };

  return (
    <Card className="route-planner-card space-y-3">
      <h2 className="flex items-center gap-2 text-sm font-bold text-foreground">
        <Navigation className="size-4 text-primary" aria-hidden />
        Plan a Route
      </h2>
      <p className="-mt-1 text-xs leading-relaxed text-text-muted">
        Start with where you are, then choose where you want to go. We will compare three estimates
        using available evidence.
      </p>

      <div className="space-y-2">
        <div className="relative">
          <MapPin
            className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-success"
            aria-hidden
          />
          <input
            type="text"
            value={origin}
            onChange={(e) => {
              setOrigin(e.target.value);
              setOriginCoords(null);
              applySuggestion(e.target.value, "origin");
            }}
            placeholder="Starting point"
            aria-label="Starting point"
            list="origin-suggestions"
            className="h-12 w-full rounded-xl border border-border bg-surface pl-10 pr-24 text-sm text-foreground transition-all duration-200 placeholder:text-text-muted focus:border-primary/40 focus:bg-surface-hover focus:outline-none"
          />
          <datalist id="origin-suggestions">
            {originOptions.map((p) => (
              <option key={p.label} value={p.label} />
            ))}
          </datalist>
          <div className="absolute top-1/2 right-1.5 flex -translate-y-1/2 items-center gap-0.5">
            {origin ? (
              <button
                type="button"
                onClick={clearOrigin}
                aria-label="Clear starting point"
                className="flex size-10 cursor-pointer items-center justify-center rounded-lg text-text-muted transition-colors hover:bg-surface-hover hover:text-foreground"
              >
                <X className="size-3.5" aria-hidden />
              </button>
            ) : null}
            <button
              type="button"
              onClick={useMyLocation}
              disabled={locating}
              aria-label="Use my current location"
              title="Use my current location"
              className="flex size-10 cursor-pointer items-center justify-center rounded-lg text-primary transition-colors hover:bg-primary/10 disabled:opacity-50"
            >
              {locating ? (
                <Loader2 className="size-3.5 animate-spin" aria-hidden />
              ) : (
                <Crosshair className="size-3.5" aria-hidden />
              )}
            </button>
          </div>
        </div>

        <div className="relative">
          <MapPin
            className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-emergency"
            aria-hidden
          />
          <input
            type="text"
            value={destination}
            onChange={(e) => {
              setDestination(e.target.value);
              setDestCoords(null);
              applySuggestion(e.target.value, "destination");
            }}
            placeholder="Destination — say it or type it"
            aria-label="Destination"
            list="dest-suggestions"
            className="h-12 w-full rounded-xl border border-border bg-surface pl-10 pr-24 text-sm text-foreground transition-all duration-200 placeholder:text-text-muted focus:border-primary/40 focus:bg-surface-hover focus:outline-none"
          />
          <datalist id="dest-suggestions">
            {destOptions.map((p) => (
              <option key={p.label} value={p.label} />
            ))}
          </datalist>
          <div className="absolute top-1/2 right-1.5 flex -translate-y-1/2 items-center gap-0.5">
            <select
              value={listenLang}
              onChange={(e) => setListenLang(e.target.value as "hi-IN" | "en-IN")}
              aria-label="Voice input language"
              className="h-10 cursor-pointer rounded-lg border border-border bg-surface px-1 text-[10px] text-text-muted focus:outline-none"
            >
              <option value="hi-IN">हिंदी</option>
              <option value="en-IN">English</option>
            </select>
            <button
              type="button"
              onClick={() => listen("destination")}
              disabled={listening}
              aria-label="Speak destination"
              title="Speak destination"
              className={`flex size-10 cursor-pointer items-center justify-center rounded-lg transition-colors disabled:opacity-50 ${
                listening
                  ? "bg-emergency/15 text-emergency animate-ring-pulse"
                  : "text-primary hover:bg-primary/10"
              }`}
            >
              <Mic className="size-3.5" aria-hidden />
            </button>
          </div>
        </div>
      </div>

      {voiceError ? (
        <div className="flex items-start gap-2 rounded-xl border border-warning/20 bg-warning/5 p-2.5 text-xs text-warning">
          <AlertCircle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
          {voiceError}
        </div>
      ) : null}

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
              className={`min-h-10 rounded-full px-3 py-1 text-[11px] font-medium transition-colors duration-150 ${
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
        Plan Route
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
