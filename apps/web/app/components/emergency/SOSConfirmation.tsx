"use client";

import { AlertTriangle, Phone, Timer, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/app/components/ui/Button";
import { Modal } from "@/app/components/ui/Modal";
import { fetchContacts, startEmergency } from "@/lib/api";
import type { EmergencySession } from "@/lib/types";
import { EmergencyStatus, SosLoading } from "./EmergencyStatus";

const HELPLINES = [
  { label: "Women Helpline", number: "181", detail: "24×7 free helpline" },
  { label: "Police", number: "112", detail: "Emergency services" },
  { label: "Ambulance", number: "102", detail: "Medical emergency" },
];

/** Client-side activation countdown (matches config emergency_countdown_default_s). */
const COUNTDOWN_S = 5;

type Phase = "options" | "countdown" | "activating" | "active" | "ended";

function formatCountdown(s: number): string {
  return String(Math.max(0, s)).padStart(2, "0");
}

export function SOSConfirmation({
  open,
  onClose,
  restoredSession,
}: {
  open: boolean;
  onClose: () => void;
  /** An already-active session (e.g. after a page reload). */
  restoredSession: EmergencySession | null;
}) {
  const [phase, setPhase] = useState<Phase>("options");
  const [seconds, setSeconds] = useState(COUNTDOWN_S);
  const [session, setSession] = useState<EmergencySession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [locating, setLocating] = useState(false);
  const positionRef = useRef<{ lat: number; lon: number } | null>(null);
  const contactIdsRef = useRef<number[]>([]);

  useEffect(() => {
    if (!open) return;
    setError(null);
    if (restoredSession) {
      setSession(restoredSession);
      setPhase("active");
    } else {
      setSession(null);
      setPhase("options");
    }
  }, [open, restoredSession]);

  const locate = (): Promise<{ lat: number; lon: number } | null> =>
    new Promise((resolve) => {
      if (!("geolocation" in navigator)) {
        resolve(null);
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
        () => resolve(null),
        { enableHighAccuracy: true, timeout: 8000 },
      );
    });

  const startCountdown = async () => {
    setError(null);
    setSeconds(COUNTDOWN_S);
    setLocating(true);
    // Fetch contacts and location in parallel while the countdown runs.
    const [position, contacts] = await Promise.all([
      locate(),
      fetchContacts().catch(() => [] as Awaited<ReturnType<typeof fetchContacts>>),
    ]);
    positionRef.current = position;
    contactIdsRef.current = contacts.filter((c) => c.enabled).map((c) => c.id);
    setLocating(false);
    setPhase("countdown");
  };

  const activate = useCallback(async () => {
    const position = positionRef.current;
    if (!position) {
      setError(
        "Location is required to start an emergency session. Allow location access or call a helpline directly.",
      );
      setPhase("options");
      return;
    }
    setPhase("activating");
    try {
      const created = await startEmergency(position.lat, position.lon, contactIdsRef.current);
      setSession(created);
      setPhase("active");
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Could not activate the emergency session. Try again or call a helpline.",
      );
      setPhase("options");
    }
  }, []);

  useEffect(() => {
    if (phase !== "countdown") return;
    if (seconds <= 0) {
      void activate();
      return;
    }
    const t = setTimeout(() => setSeconds((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [phase, seconds, activate]);

  const cancelCountdown = () => {
    setPhase("options");
    setSeconds(COUNTDOWN_S);
  };

  const handleClose = () => {
    if (phase === "countdown") {
      cancelCountdown();
      return;
    }
    if (phase === "activating" || phase === "active") return;
    onClose();
  };

  return (
    <Modal open={open} onClose={handleClose} title="Emergency">
      {phase === "options" ? (
        <div className="space-y-4">
          <div className="flex flex-col items-center gap-3 py-2 text-center">
            <span className="flex size-16 items-center justify-center rounded-full bg-emergency/15 text-emergency animate-ring-pulse">
              <AlertTriangle className="size-7" aria-hidden />
            </span>
            <p className="text-sm text-text-secondary">
              Call emergency services, or activate SOS to share your live location with your trusted
              contacts.
            </p>
          </div>

          <div className="space-y-2">
            {HELPLINES.map((c) => (
              <a
                key={c.number}
                href={`tel:${c.number}`}
                className="flex items-center gap-3 rounded-xl border border-border bg-surface p-3 transition-colors hover:border-emergency/30 hover:bg-emergency/5"
              >
                <Phone className="size-4 text-emergency" aria-hidden />
                <div className="flex-1">
                  <p className="text-sm font-semibold text-foreground">{c.label}</p>
                  <p className="text-xs text-text-muted">{c.detail}</p>
                </div>
                <span className="text-sm font-bold text-emergency">{c.number}</span>
              </a>
            ))}
          </div>

          <Button
            variant="danger"
            fullWidth
            size="lg"
            loading={locating}
            onClick={() => void startCountdown()}
          >
            <AlertTriangle className="size-4" aria-hidden /> Activate SOS
          </Button>

          {error ? (
            <p className="rounded-lg border border-emergency/30 bg-emergency/8 px-3 py-2 text-xs text-emergency">
              {error}
            </p>
          ) : null}

          <Button variant="secondary" fullWidth onClick={handleClose}>
            <X className="size-4" aria-hidden /> Cancel
          </Button>
        </div>
      ) : null}

      {phase === "countdown" ? (
        <div
          role="status"
          aria-live="polite"
          className="flex flex-col items-center gap-4 py-4 text-center"
        >
          <span className="flex size-24 items-center justify-center rounded-full bg-emergency text-white shadow-lg shadow-emergency/25 animate-ring-pulse">
            <span className="font-display text-4xl font-bold tabular-nums">
              {formatCountdown(seconds)}
            </span>
          </span>
          <div>
            <p className="text-sm font-semibold text-foreground">SOS activates in {seconds}s</p>
            <p className="mt-1 text-xs text-text-muted">
              Your live location will be shared with your enabled trusted contacts.
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-text-muted">
            <Timer className="size-3.5" aria-hidden />
            {locating ? "Getting your location…" : "Location ready"}
          </div>
          <Button variant="secondary" fullWidth onClick={cancelCountdown}>
            <X className="size-4" aria-hidden /> Cancel SOS
          </Button>
        </div>
      ) : null}

      {phase === "activating" ? <SosLoading /> : null}

      {phase === "active" && session ? (
        <EmergencyStatus session={session} onEnded={() => setPhase("ended")} />
      ) : null}

      {phase === "ended" ? (
        <div className="flex flex-col items-center gap-3 py-6 text-center">
          <span className="flex size-14 items-center justify-center rounded-full bg-success/15 text-success">
            <AlertTriangle className="size-6" aria-hidden />
          </span>
          <p className="text-sm font-semibold text-foreground">SOS ended</p>
          <p className="text-xs text-text-muted">
            The emergency session was ended and your location is no longer shared.
          </p>
          <Button variant="primary" fullWidth onClick={onClose}>
            Done
          </Button>
        </div>
      ) : null}
    </Modal>
  );
}
