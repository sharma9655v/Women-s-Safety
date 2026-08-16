"use client";

import { Loader2, Volume2, VolumeX } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/app/components/ui/Badge";
import { Button } from "@/app/components/ui/Button";
import { Card, CardHeader } from "@/app/components/ui/Card";
import { fetchVoiceGuidanceStatus, startVoiceGuidance, stopVoiceGuidance } from "@/lib/api";
import type { VoiceGuidanceStatus } from "@/lib/types";

const POLL_MS = 15000;

const speechSupported = (): boolean => typeof window !== "undefined" && "speechSynthesis" in window;

export function VoiceGuidanceCard() {
  const [status, setStatus] = useState<VoiceGuidanceStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unsupported, setUnsupported] = useState(false);

  useEffect(() => {
    setUnsupported(!speechSupported());
  }, []);

  const refresh = useCallback(() => {
    fetchVoiceGuidanceStatus()
      .then(setStatus)
      .catch(() => {
        /* poll retries */
      });
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchVoiceGuidanceStatus()
      .then((s) => {
        if (!cancelled) setStatus(s);
      })
      .catch(() => {
        if (!cancelled) setStatus(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!status?.active) return;
    const t = setInterval(refresh, POLL_MS);
    return () => clearInterval(t);
  }, [status?.active, refresh]);

  const start = async () => {
    if (unsupported || busy) return;
    setBusy(true);
    setError(null);
    try {
      const started = await startVoiceGuidance("en", null);
      if (!started.active) {
        setError("Voice guidance did not start. Try again.");
      } else {
        setStatus(started);
        try {
          window.speechSynthesis.cancel();
        } catch {
          // speech engine unavailable — the session is still tracked
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start voice guidance. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const stop = async () => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      setStatus(await stopVoiceGuidance());
      try {
        window.speechSynthesis.cancel();
      } catch {
        // nothing to stop
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not stop voice guidance. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const active = status?.active === true;

  return (
    <Card className="border-primary/15">
      <CardHeader
        title="Voice guidance"
        subtitle="Spoken safety cues while the session is active."
        action={active ? <Badge tone="success">Active</Badge> : undefined}
      />
      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {active ? (
            <Volume2 className="size-4" aria-hidden />
          ) : (
            <VolumeX className="size-4" aria-hidden />
          )}
        </span>
        <div className="min-w-0 flex-1">
          {unsupported ? (
            <p className="text-xs text-text-muted">
              Voice guidance is not supported in this browser.
            </p>
          ) : loading ? (
            <div className="flex items-center gap-2 py-1 text-sm text-text-muted">
              <Loader2 className="size-4 animate-spin" aria-hidden /> Checking status…
            </div>
          ) : (
            <div className="space-y-2.5">
              <p className="text-xs text-text-muted">
                {active
                  ? "Voice guidance is active on this device. It uses your browser's speech engine — prompts are read aloud as the app guides you."
                  : "Start a voice guidance session. Spoken cues come from your browser's speech engine; audio quality depends on the device."}
              </p>
              {active ? (
                <Button variant="outline" size="sm" loading={busy} onClick={() => void stop()}>
                  <VolumeX className="size-3.5" aria-hidden /> Stop voice guidance
                </Button>
              ) : (
                <Button size="sm" loading={busy} onClick={() => void start()}>
                  <Volume2 className="size-3.5" aria-hidden /> Start voice guidance
                </Button>
              )}
            </div>
          )}
          {error ? <p className="mt-2 text-xs text-danger">{error}</p> : null}
        </div>
      </div>
    </Card>
  );
}
