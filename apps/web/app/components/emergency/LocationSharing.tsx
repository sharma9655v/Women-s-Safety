"use client";

import { Loader2, MapPin, Shield, Timer } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Badge } from "@/app/components/ui/Badge";
import { Button } from "@/app/components/ui/Button";
import { Card, CardHeader } from "@/app/components/ui/Card";
import { fetchActiveSharing, startSharing, stopSharing, updateSharingLocation } from "@/lib/api";
import type { SharingSession } from "@/lib/types";

const TTL_S = 1800; // 30 minutes, within the backend max

function formatRemaining(expiresAt: string): string {
  const ms = Math.max(0, new Date(expiresAt).getTime() - Date.now());
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function LocationSharing() {
  const [session, setSession] = useState<SharingSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [, setTick] = useState(0);
  const watchRef = useRef<number | null>(null);
  const locationRef = useRef<{ lat: number; lon: number } | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchActiveSharing()
      .then((s) => {
        if (!cancelled) setSession(s);
      })
      .catch(() => {
        if (!cancelled) setError("Location sharing is unavailable right now.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Countdown + live location while a session is active.
  useEffect(() => {
    if (session?.status !== "ACTIVE") return;
    const t = setInterval(() => setTick((v) => v + 1), 1000);
    return () => clearInterval(t);
  }, [session]);

  useEffect(() => {
    if (session?.status !== "ACTIVE") return;
    if (!("geolocation" in navigator)) {
      setLocationError("Location sharing is not supported by this browser.");
      return;
    }
    watchRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        setLocationError(null);
        locationRef.current = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        void updateSharingLocation(session.session_id, pos.coords.latitude, pos.coords.longitude)
          .then(setSession)
          .catch(() => {
            // keep the last known session state; location will retry
          });
      },
      () => {
        setLocationError("Location fix lost — contacts may see an outdated position.");
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 30000 },
    );
    return () => {
      if (watchRef.current !== null) {
        navigator.geolocation.clearWatch(watchRef.current);
        watchRef.current = null;
      }
    };
  }, [session]);

  const start = async () => {
    setStarting(true);
    setError(null);
    try {
      const created = await startSharing("GUARDIAN", TTL_S, []);
      setSession(created);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start location sharing. Try again.");
    } finally {
      setStarting(false);
    }
  };

  const stop = async () => {
    if (!session) return;
    try {
      await stopSharing(session.session_id);
      setSession(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not stop sharing. Try again.");
    }
  };

  const active = session?.status === "ACTIVE";

  return (
    <Card className="border-info/20">
      <CardHeader
        title="Share your location"
        subtitle="Live location, shared only while you keep the session active."
        action={active ? <Badge tone="info">Active</Badge> : undefined}
      />
      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-info/15 text-info">
          <MapPin className="size-4" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          {loading ? (
            <div className="flex items-center gap-2 py-1 text-sm text-text-muted">
              <Loader2 className="size-4 animate-spin" aria-hidden /> Checking status…
            </div>
          ) : active && session ? (
            <div className="space-y-2">
              <p className="text-sm text-foreground">
                {session.latitude !== null && session.longitude !== null
                  ? `${session.latitude.toFixed(5)}, ${session.longitude.toFixed(5)}`
                  : "Waiting for a location fix…"}
              </p>
              <p className="flex items-center gap-1.5 text-xs text-text-muted">
                <Timer className="size-3.5" aria-hidden />
                Stops automatically in {formatRemaining(session.expires_at)}
              </p>
              <p className="flex items-center gap-1.5 text-[10px] text-text-muted">
                <Shield className="size-3" aria-hidden />
                Explicit opt-in only · always revocable
              </p>
              {locationError ? (
                <p className="rounded-lg border border-warning/25 bg-warning/10 px-2.5 py-2 text-xs text-warning">
                  {locationError}
                </p>
              ) : null}
              <Button variant="danger" size="sm" onClick={() => void stop()}>
                Stop sharing
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-text-muted">
                Your live location is sent to the backend and readable by your trusted contacts
                while the session is active. It stops automatically after 30 minutes or when you
                stop it.
              </p>
              <div className="flex items-center gap-1.5 text-[10px] text-text-muted">
                <Shield className="size-3" aria-hidden />
                Explicit opt-in only · auto-expires
              </div>
              <Button variant="primary" size="sm" loading={starting} onClick={() => void start()}>
                <MapPin className="size-3.5" aria-hidden /> Start sharing
              </Button>
            </div>
          )}
          {error ? <p className="mt-2 text-xs text-danger">{error}</p> : null}
        </div>
      </div>
    </Card>
  );
}
