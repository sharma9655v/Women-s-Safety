"use client";

import { CheckCircle2, CircleCheckBig, Flag, Loader2, MapPin, Timer } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/app/components/ui/Badge";
import { Button } from "@/app/components/ui/Button";
import { Card, CardHeader } from "@/app/components/ui/Card";
import { Input } from "@/app/components/ui/Input";
import {
  checkinJourney,
  endJourneyCheckin,
  fetchActiveJourneyCheckin,
  fetchContacts,
  startJourneyCheckin,
} from "@/lib/api";
import type { JourneyCheckinSession, TrustedContact } from "@/lib/types";

const POLL_MS = 15000;

function formatDeadline(iso: string | null): string {
  if (!iso) return "—";
  const ms = Math.max(0, new Date(iso).getTime() - Date.now());
  if (ms <= 0) return "Due now";
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  return `${m}m ${total % 60}s`;
}

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

interface JourneySummary {
  session: JourneyCheckinSession;
  ended_at: string;
  end_reason: string;
}

export function JourneyCheckinCard() {
  const [session, setSession] = useState<JourneyCheckinSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [contacts, setContacts] = useState<TrustedContact[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [destination, setDestination] = useState("");
  const [etaMinutes, setEtaMinutes] = useState("30");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<JourneySummary | null>(null);
  const [, setTick] = useState(0);

  const refresh = useCallback(() => {
    fetchActiveJourneyCheckin()
      .then(setSession)
      .catch(() => {
        /* poll retries */
      });
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchActiveJourneyCheckin()
      .then((s) => {
        if (!cancelled) setSession(s);
      })
      .catch(() => {
        if (!cancelled) setError("Check-in is unavailable right now.");
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
    const t = setInterval(() => {
      setTick((v) => v + 1);
      refresh();
    }, POLL_MS);
    return () => clearInterval(t);
  }, [session, refresh]);

  useEffect(() => {
    if (session) return;
    fetchContacts()
      .then(setContacts)
      .catch(() => setContacts([]));
  }, [session]);

  const toggleContact = (id: number) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]));
  };

  const start = async () => {
    if (!destination.trim()) {
      setError("Tell us your destination to start a check-in journey.");
      return;
    }
    if (selected.length === 0) {
      setError("Choose at least one trusted contact.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await startJourneyCheckin({
        destination_name: destination.trim(),
        destination_lat: null,
        destination_lon: null,
        expected_arrival_at:
          etaMinutes && Number(etaMinutes) > 0
            ? new Date(Date.now() + Number(etaMinutes) * 60000).toISOString()
            : null,
        checkin_interval_s: 900,
        checkin_grace_s: 300,
        contact_ids: selected,
      });
      setSession(created);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start the check-in journey.");
    } finally {
      setBusy(false);
    }
  };

  const checkin = async () => {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      setSession(await checkinJourney(session.session_id));
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
      const result = await endJourneyCheckin(session.session_id, reason);
      setSummary({ session, ended_at: result.ended_at, end_reason: result.end_reason });
      setSession(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not end the journey.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="border-info/20">
      <CardHeader
        title="Journey check-in"
        subtitle="Share a journey with trusted contacts; they are only notified if you miss a check-in."
        action={session ? <Badge tone="success">Active</Badge> : undefined}
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
          ) : summary ? (
            <div className="space-y-2.5">
              <p className="flex items-center gap-1.5 text-sm text-foreground">
                <CircleCheckBig
                  className={`size-4 ${
                    summary.end_reason === "arrived" ? "text-success" : "text-text-muted"
                  }`}
                  aria-hidden
                />
                {summary.end_reason === "arrived" ? "Journey completed" : "Journey ended"}
              </p>
              <p className="text-xs text-text-muted">
                {summary.session.destination_name ?? "Your destination"} ·{" "}
                {summary.end_reason === "arrived" ? "arrived" : "ended"} at{" "}
                <span className="font-medium text-foreground">{fmtTime(summary.ended_at)}</span>
              </p>
              <ol className="space-y-0">
                {[
                  {
                    icon: MapPin,
                    label: "Journey started",
                    time: summary.session.started_at,
                  },
                  ...(summary.session.last_checkin_at
                    ? [
                        {
                          icon: CheckCircle2,
                          label: "Last check-in",
                          time: summary.session.last_checkin_at,
                        },
                      ]
                    : []),
                  {
                    icon: Flag,
                    label:
                      summary.end_reason === "arrived" ? "Arrived at destination" : "Journey ended",
                    time: summary.ended_at,
                  },
                ].map((step, i, all) => {
                  const Icon = step.icon;
                  const isLast = i === all.length - 1;
                  return (
                    <li key={step.label} className="flex items-start gap-2.5">
                      <div className="flex flex-col items-center">
                        <span
                          className={`flex size-5 shrink-0 items-center justify-center rounded-full ${
                            isLast ? "bg-success/15 text-success" : "bg-info/15 text-info"
                          }`}
                        >
                          <Icon className="size-3" aria-hidden />
                        </span>
                        {!isLast ? <span className="mt-0.5 w-px flex-1 bg-border" /> : null}
                      </div>
                      <div className="pb-2.5">
                        <p className="text-xs font-medium text-foreground">{step.label}</p>
                        <p className="text-[11px] text-text-muted">{fmtTime(step.time)}</p>
                      </div>
                    </li>
                  );
                })}
              </ol>
              <p className="text-[11px] text-text-muted">
                Check-in interval {Math.round(summary.session.checkin_interval_s / 60)} min · grace{" "}
                {Math.round(summary.session.checkin_grace_s / 60)} min ·{" "}
                {summary.session.escalation_stage > 0
                  ? `escalation stage ${summary.session.escalation_stage} was reached`
                  : "your trusted contacts were never notified during this journey"}
                .
              </p>
              <Button variant="outline" size="sm" onClick={() => setSummary(null)}>
                Start another journey
              </Button>
            </div>
          ) : session ? (
            <div className="space-y-2.5">
              <p className="flex items-center gap-1.5 text-sm text-foreground">
                <Timer className="size-3.5 text-info" aria-hidden />
                Next check-in in{" "}
                <span className="font-semibold">{formatDeadline(session.next_checkin_at)}</span>
              </p>
              <p className="text-xs text-text-muted">
                Heading to{" "}
                <span className="font-medium text-foreground">
                  {session.destination_name ?? "your destination"}
                </span>
                {session.expected_arrival_at
                  ? ` · expected by ${new Date(session.expected_arrival_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}`
                  : ""}
              </p>
              <p className="text-[11px] text-text-muted">
                Last check-in:{" "}
                {session.last_checkin_at
                  ? new Date(session.last_checkin_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : "journey start"}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button variant="success" size="sm" loading={busy} onClick={() => void checkin()}>
                  <CheckCircle2 className="size-3.5" aria-hidden /> I&apos;m okay
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
                Start a timed journey. If you do not check in on time, your trusted contacts are
                notified in-app (no external delivery yet).
              </p>
              <Input
                id="checkin-destination"
                label="Destination"
                placeholder="Where are you going?"
                value={destination}
                maxLength={80}
                onChange={(e) => setDestination(e.target.value)}
              />
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
                          ? "border-info/40 bg-info/15 text-info"
                          : "border-border bg-surface-hover text-text-secondary hover:border-info/30"
                      }`}
                    >
                      {c.name}
                    </button>
                  ))}
                </div>
              )}
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
              <Button variant="outline" size="sm" loading={busy} onClick={() => void start()}>
                <MapPin className="size-3.5" aria-hidden /> Start check-in journey
              </Button>
            </div>
          )}
          {error ? <p className="mt-2 text-xs text-danger">{error}</p> : null}
        </div>
      </div>
    </Card>
  );
}
