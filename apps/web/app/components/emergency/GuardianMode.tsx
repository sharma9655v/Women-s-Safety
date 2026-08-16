"use client";

import { CheckCircle2, Loader2, Route as RouteIcon, Shield, Timer } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Badge } from "@/app/components/ui/Badge";
import { Button } from "@/app/components/ui/Button";
import { Card, CardHeader } from "@/app/components/ui/Card";
import {
  checkInGuardian,
  endGuardian,
  fetchActiveGuardian,
  fetchContacts,
  startGuardian,
  updateGuardianLocation,
} from "@/lib/api";
import type { GuardianSession, TrustedContact } from "@/lib/types";

/** Poll the active session so server-side escalation is reflected. */
const POLL_MS = 15000;

function formatDeadline(deadline: string): string {
  const ms = Math.max(0, new Date(deadline).getTime() - Date.now());
  if (ms <= 0) return "Overdue";
  const total = Math.floor(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h > 0
    ? `${h}h ${String(m).padStart(2, "0")}m ${String(s).padStart(2, "0")}s`
    : `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/**
 * Guardian mode: check-in companion journey. The check-in deadline, escalation
 * stage and deviation flags come from the backend — this card never invents
 * escalation or contact states.
 */
export function GuardianMode({
  plannedGeometry,
}: {
  /** Route geometry ([lon, lat] pairs) of the journey, if the user planned one. */
  plannedGeometry?: [number, number][] | null;
}) {
  const [session, setSession] = useState<GuardianSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [contacts, setContacts] = useState<TrustedContact[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [etaMinutes, setEtaMinutes] = useState("30");
  const [monitorRoute, setMonitorRoute] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [, setTick] = useState(0);
  const watchRef = useRef<number | null>(null);
  const sessionRef = useRef<GuardianSession | null>(null);
  sessionRef.current = session;

  const refresh = useCallback(() => {
    fetchActiveGuardian()
      .then(setSession)
      .catch(() => {
        /* keep last known state; poll retries */
      });
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchActiveGuardian()
      .then((s) => {
        if (!cancelled) setSession(s);
      })
      .catch(() => {
        if (!cancelled) setError("Guardian mode is unavailable right now.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!session) return;
    const t = setInterval(refresh, POLL_MS);
    return () => clearInterval(t);
  }, [session, refresh]);

  // Countdown tick while a journey is active.
  useEffect(() => {
    if (!session) return;
    const t = setInterval(() => setTick((v) => v + 1), 1000);
    return () => clearInterval(t);
  }, [session]);

  // Live location while the journey is active.
  useEffect(() => {
    if (!session) return;
    if (!("geolocation" in navigator)) {
      setLocationError("Location sharing is not supported by this browser.");
      return;
    }
    watchRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        setLocationError(null);
        void updateGuardianLocation(
          sessionRef.current?.session_id ?? "",
          pos.coords.latitude,
          pos.coords.longitude,
        )
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

  const pickContacts = useCallback(async () => {
    try {
      setContacts(await fetchContacts());
    } catch {
      setContacts([]);
    }
  }, []);

  useEffect(() => {
    if (!session) void pickContacts();
  }, [session, pickContacts]);

  const toggleContact = (id: number) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]));
  };

  const start = async () => {
    if (selected.length === 0) {
      setError("Choose at least one trusted contact to guard this journey.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const eta = etaMinutes && Number(etaMinutes) > 0 ? Number(etaMinutes) : null;
      const created = await startGuardian({
        guardian_contact_ids: selected,
        expected_arrival_at: eta !== null ? new Date(Date.now() + eta * 60000).toISOString() : null,
        planned_geometry: monitorRoute ? (plannedGeometry ?? null) : null,
      });
      setSession(created);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start guardian mode. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const checkin = async () => {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      setSession(await checkInGuardian(session.session_id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not check in. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const end = async (reason: "arrived" | "cancelled") => {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      await endGuardian(session.session_id, reason);
      setSession(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not end the journey. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const statusBadge = session ? (
    session.status === "ESCALATED" ? (
      <Badge tone="danger">Escalated</Badge>
    ) : session.deviation_detected ? (
      <Badge tone="warning">Off route</Badge>
    ) : (
      <Badge tone="success">Active</Badge>
    )
  ) : undefined;

  return (
    <Card className="border-success/20">
      <CardHeader
        title="Guardian mode"
        subtitle="Check in regularly while you travel; trusted contacts are notified only if you miss a check-in."
        action={statusBadge}
      />
      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-success/15 text-success">
          <Shield className="size-4" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          {loading ? (
            <div className="flex items-center gap-2 py-1 text-sm text-text-muted">
              <Loader2 className="size-4 animate-spin" aria-hidden /> Checking status…
            </div>
          ) : session ? (
            <div className="space-y-2.5">
              <p className="flex items-center gap-1.5 text-sm text-foreground">
                <Timer className="size-3.5 text-success" aria-hidden />
                Check-in due in{" "}
                <span className="font-semibold">{formatDeadline(session.checkin_deadline)}</span>
              </p>

              {session.escalation_stage >= 1 ? (
                <p className="rounded-lg border border-warning/25 bg-warning/10 px-2.5 py-2 text-xs text-warning">
                  {session.escalation_stage >= 2
                    ? "A check-in was missed and your trusted contacts were notified in-app. Delivery is not guaranteed — call for help if you are unsafe."
                    : "A check-in was missed. Your trusted contacts will be notified if you do not check in soon."}
                </p>
              ) : null}

              {session.deviation_detected ? (
                <p className="rounded-lg border border-warning/25 bg-warning/10 px-2.5 py-2 text-xs text-warning">
                  You are off your planned route
                  {session.first_deviation_at
                    ? ` since ${formatTime(session.first_deviation_at)}`
                    : ""}
                  . Your contacts have been notified in-app.
                </p>
              ) : null}

              <p className="flex items-center gap-1.5 text-xs text-text-muted">
                <CheckCircle2 className="size-3.5 text-success" aria-hidden />
                Last check-in:{" "}
                {session.last_checkin_at ? formatTime(session.last_checkin_at) : "at journey start"}
              </p>

              {locationError ? (
                <p className="rounded-lg border border-warning/25 bg-warning/10 px-2.5 py-2 text-xs text-warning">
                  {locationError}
                </p>
              ) : null}

              <div className="flex flex-wrap gap-2">
                <Button variant="success" size="sm" loading={busy} onClick={() => void checkin()}>
                  <CheckCircle2 className="size-3.5" aria-hidden /> Check in — I&apos;m okay
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  loading={busy}
                  onClick={() => void end("arrived")}
                >
                  I&apos;ve arrived
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  loading={busy}
                  onClick={() => void end("cancelled")}
                >
                  End journey
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-2.5">
              <p className="text-xs text-text-muted">
                Choose trusted contacts to guard this journey. If you do not check in by the
                deadline, they are notified in-app (no external delivery yet), and you can still end
                the journey anytime.
              </p>

              {contacts.length === 0 ? (
                <p className="rounded-lg border border-border bg-surface-hover px-2.5 py-2 text-xs text-text-muted">
                  No trusted contacts yet. Add some on the{" "}
                  <a href="/contacts" className="text-primary underline">
                    Trusted Contacts
                  </a>{" "}
                  page first.
                </p>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {contacts.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => toggleContact(c.id)}
                      className={`rounded-lg border px-2.5 py-1 text-xs transition-colors ${
                        selected.includes(c.id)
                          ? "border-success/40 bg-success/15 text-success"
                          : "border-border bg-surface-hover text-text-secondary hover:border-success/30"
                      }`}
                    >
                      {c.name}
                    </button>
                  ))}
                </div>
              )}

              <div className="flex flex-wrap items-center gap-2">
                <label className="flex items-center gap-1.5 text-xs text-text-muted">
                  Expected arrival in
                  <input
                    type="number"
                    min={1}
                    max={720}
                    value={etaMinutes}
                    onChange={(e) => setEtaMinutes(e.target.value)}
                    className="w-14 rounded-lg border border-border bg-surface px-2 py-1 text-xs text-foreground"
                  />
                  min
                </label>
                {plannedGeometry && plannedGeometry.length > 0 ? (
                  <label className="flex cursor-pointer items-center gap-1.5 text-xs text-text-muted">
                    <input
                      type="checkbox"
                      checked={monitorRoute}
                      onChange={(e) => setMonitorRoute(e.target.checked)}
                      className="size-3.5 accent-success"
                    />
                    <RouteIcon className="size-3.5" aria-hidden /> Check me against my planned route
                  </label>
                ) : null}
              </div>

              <Button variant="success" size="sm" loading={busy} onClick={() => void start()}>
                <Shield className="size-3.5" aria-hidden /> Start guardian journey
              </Button>
            </div>
          )}
          {error ? <p className="mt-2 text-xs text-danger">{error}</p> : null}
        </div>
      </div>
    </Card>
  );
}
