"use client";

import { Loader2, Phone, PhoneCall, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/app/components/ui/Badge";
import { Button } from "@/app/components/ui/Button";
import { Card, CardHeader } from "@/app/components/ui/Card";
import { Input } from "@/app/components/ui/Input";
import { fetchFakeCall, fetchFakeCallStatus, startFakeCall } from "@/lib/api";
import type { FakeCallSession } from "@/lib/types";

const POLL_MS = 10000;

const STATUS_TONE: Record<FakeCallSession["status"], "success" | "warning" | "info" | "default"> = {
  SCHEDULED: "info",
  TRIGGERED: "success",
  DISMISSED: "default",
  EXPIRED: "default",
};

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function FakeCallCard() {
  const [session, setSession] = useState<FakeCallSession | null>(null);
  const [caller, setCaller] = useState("Mom");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setSession((prev) => {
      if (!prev) return prev;

      fetchFakeCall(prev.id)
        .then(setSession)
        .catch(() => {
          /* poll retries */
        });

      return prev;
    });
  }, []);

  useEffect(() => {
    let cancelled = false;

    fetchFakeCallStatus()
      .then((s) => {
        if (!cancelled) setSession(s);
      })
      .catch(() => {
        if (!cancelled) setSession(null);
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

  const trigger = async () => {
    if (!caller.trim()) return;

    setBusy(true);
    setError(null);

    try {
      const created = await startFakeCall({
        caller_name: caller.trim(),
      });

      setSession(created);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start the fake call. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const running = session && (session.status === "SCHEDULED" || session.status === "TRIGGERED");

  return (
    <Card className="border-info/20">
      <CardHeader
        title="Fake incoming call"
        subtitle="Simulated call so you can step away — no one is actually calling."
        action={
          session ? <Badge tone={STATUS_TONE[session.status]}>{session.status}</Badge> : undefined
        }
      />

      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-info/15 text-info">
          <Phone className="size-4" aria-hidden />
        </span>

        <div className="min-w-0 flex-1">
          {loading ? (
            <div className="flex items-center gap-2 py-1 text-sm text-text-muted">
              <Loader2 className="size-4 animate-spin" aria-hidden />
              Checking status…
            </div>
          ) : running ? (
            <div className="space-y-2.5">
              <p className="flex items-center gap-1.5 text-sm text-foreground">
                <PhoneCall className="size-3.5 text-info" aria-hidden />
                Incoming call from <span className="font-semibold">{session.caller_name}</span>
              </p>

              <p className="text-xs text-text-muted">
                Triggered at {formatTime(session.scheduled_at)} — pretend to answer and walk away.
                It is only an app simulation.
              </p>

              {session.status === "SCHEDULED" ? (
                <p className="text-[11px] text-text-muted">
                  Scheduled — it will ring shortly. Polling for status…
                </p>
              ) : null}

              <Button
                variant="ghost"
                size="sm"
                onClick={() => void refresh()}
                aria-label="Refresh fake call status"
              >
                <RefreshCw className="size-3.5" aria-hidden />
                Refresh status
              </Button>
            </div>
          ) : (
            <div className="space-y-2.5">
              <p className="text-xs text-text-muted">
                Give yourself a believable excuse to leave. The caller is simulated — nobody is on
                the line.
              </p>

              <div className="flex gap-2">
                <Input
                  id="fake-call-caller"
                  aria-label="Caller name"
                  value={caller}
                  maxLength={30}
                  onChange={(e) => setCaller(e.target.value)}
                  className="h-9"
                />

                <Button size="sm" loading={busy} onClick={() => void trigger()}>
                  <PhoneCall className="size-3.5" aria-hidden />
                  Trigger call
                </Button>
              </div>
            </div>
          )}

          {error ? <p className="mt-2 text-xs text-danger">{error}</p> : null}
        </div>
      </div>
    </Card>
  );
}
