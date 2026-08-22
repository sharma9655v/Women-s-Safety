"use client";

import { AlertTriangle, Loader2, MapPin, Phone, Timer } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/app/components/ui/Button";
import { endEmergency } from "@/lib/api";
import type { EmergencySession } from "@/lib/types";

function formatElapsed(startedAt: string): string {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000));
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/** Honest delivery label — never claims a contact was notified. */
export function notifyStatusLabel(status: string): { label: string; detail: string } {
  switch (status) {
    case "queued":
      return {
        label: "Notification queued",
        detail: "Your emergency is being delivered to the configured channel.",
      };
    case "sent":
      return {
        label: "Notification sent",
        detail: "The configured channel received your emergency.",
      };
    case "failed":
      return {
        label: "Notification failed",
        detail: "Delivery to the configured channel failed.",
      };
    default:
      return {
        label: "No channel configured",
        detail:
          "This deployment has no SMS/Telegram provider, so your trusted contacts were NOT notified automatically. Call helplines directly.",
      };
  }
}

export function EmergencyStatus({
  session,
  onEnded,
}: {
  session: EmergencySession;
  onEnded: () => void;
}) {
  const [, setTick] = useState(0);
  const [ending, setEnding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endedRef = useRef(false);

  useEffect(() => {
    const t = setInterval(() => setTick((v) => v + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const notify = notifyStatusLabel(session.notify_status);

  const end = async () => {
    if (endedRef.current) return;
    endedRef.current = true;
    setEnding(true);
    try {
      await endEmergency(session.session_id, "ended_by_user");
      onEnded();
    } catch {
      endedRef.current = false;
      setEnding(false);
      setError("Could not end the session. Check the connection and try again.");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col items-center gap-3 py-1 text-center">
        <span className="flex size-16 items-center justify-center rounded-full bg-emergency text-white animate-ring-pulse">
          <AlertTriangle className="size-7" aria-hidden />
        </span>
        <div>
          <p className="text-base font-bold text-emergency">Emergency active</p>
          <p className="mt-1 flex items-center justify-center gap-1.5 text-xs text-text-muted">
            <Timer className="size-3.5" aria-hidden />
            Elapsed {formatElapsed(session.started_at)}
          </p>
        </div>
      </div>

      <div className="space-y-2 rounded-xl border border-border bg-surface/60 p-3">
        <p className="flex items-center gap-2 text-sm text-foreground">
          <MapPin className="size-4 text-primary" aria-hidden />
          {session.latitude !== null && session.longitude !== null
            ? `${session.latitude.toFixed(5)}, ${session.longitude.toFixed(5)}`
            : "Location pending"}
        </p>
        <div
          className={`rounded-lg border px-2.5 py-2 text-xs ${
            notify.label === "No channel configured"
              ? "border-warning/30 bg-warning/8 text-warning"
              : "border-info/30 bg-info/8 text-info"
          }`}
        >
          <p className="font-semibold">{notify.label}</p>
          <p className="mt-0.5 text-text-muted">{notify.detail}</p>
        </div>
      </div>

      {error ? (
        <p className="rounded-lg border border-emergency/30 bg-emergency/8 px-3 py-2 text-xs text-emergency">
          {error}
        </p>
      ) : null}

      <Button variant="danger" fullWidth loading={ending} onClick={end}>
        End SOS
      </Button>
      <div className="space-y-1.5">
        {[
          { label: "Women Helpline", number: "181" },
          { label: "Police", number: "112" },
          { label: "Ambulance", number: "102" },
        ].map((c) => (
          <a
            key={c.number}
            href={`tel:${c.number}`}
            className="flex items-center justify-between rounded-xl border border-border bg-surface px-3 py-2 text-sm text-foreground transition-colors hover:border-emergency/30"
          >
            <span>{c.label}</span>
            <span className="font-bold text-emergency">{c.number}</span>
            <Phone className="size-3.5 text-emergency" aria-hidden />
          </a>
        ))}
      </div>
    </div>
  );
}

export function SosLoading() {
  return (
    <div className="flex flex-col items-center gap-3 py-6 text-center">
      <Loader2 className="size-7 animate-spin text-emergency" aria-hidden />
      <p className="text-sm text-text-muted">Activating emergency session…</p>
    </div>
  );
}
