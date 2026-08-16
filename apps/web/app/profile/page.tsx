"use client";

import { KeyRound, LogOut, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/app/components/ui/Button";
import { Card, CardHeader } from "@/app/components/ui/Card";
import { revokeDeviceSession } from "@/lib/api";
import { clientId } from "@/lib/client-id";

export default function ProfilePage() {
  const [cid, setCid] = useState("");
  const [mounted, setMounted] = useState(false);
  const [revoking, setRevoking] = useState(false);
  const [revoked, setRevoked] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    try {
      setCid(clientId());
    } catch {
      // identity unavailable (SSR / storage blocked)
    }
  }, []);

  const revoke = async () => {
    setRevoking(true);
    setError(null);
    try {
      await revokeDeviceSession();
      setRevoked(true);
      setCid("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not revoke the session. Try again.");
    } finally {
      setRevoking(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl space-y-4 p-4 lg:p-6">
        <header>
          <h1 className="text-xl font-bold text-foreground">
            <span className="text-primary">Profile</span>
          </h1>
          <p className="text-sm text-text-muted">
            This app has no accounts. You are identified by a random device id stored only in this
            browser.
          </p>
        </header>

        <Card>
          <CardHeader
            title="Device identity"
            subtitle="Pseudonymous — never linked to a name, email or phone number."
            action={
              <span className="flex items-center gap-1 text-[11px] text-text-muted">
                <ShieldCheck className="size-3.5 text-success" aria-hidden /> No account needed
              </span>
            }
          />
          <div className="space-y-3">
            <div className="rounded-xl border border-border bg-surface p-3">
              <p className="flex items-center gap-1.5 text-xs text-text-muted">
                <KeyRound className="size-3.5" aria-hidden /> Device id (hashed on the server)
              </p>
              <p className="mt-1 break-all font-mono text-xs text-foreground">
                {mounted
                  ? revoked
                    ? "Forgotten — a new one will be generated on your next visit."
                    : cid
                  : "…"}
              </p>
            </div>
            <ul className="space-y-1.5 text-xs text-text-muted">
              <li>• Cleared when you clear browser data for this site.</li>
              <li>• The backend stores only a hash of it and never ties it to personal data.</li>
              <li>• Reports stay anonymous — you cannot be listed as an author.</li>
            </ul>
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Device session"
            subtitle="Revoke the bearer token this browser uses for your safety features."
          />
          <div className="space-y-3">
            <p className="text-xs text-text-muted">
              Revoking signs this device out of SOS, guardian mode, contacts and notifications on
              the server. Your local device id is forgotten too.
            </p>
            {error ? (
              <p className="rounded-lg border border-danger/25 bg-danger/10 px-3 py-2 text-xs text-danger">
                {error}
              </p>
            ) : null}
            {revoked ? (
              <p className="rounded-lg border border-success/25 bg-success/8 px-3 py-2 text-xs text-success">
                Session revoked. Your safety features will start fresh on the next visit.
              </p>
            ) : (
              <Button
                variant="danger"
                loading={revoking}
                disabled={!mounted || revoking}
                onClick={() => void revoke()}
              >
                <LogOut className="size-3.5" aria-hidden /> Revoke this device session
              </Button>
            )}
          </div>
        </Card>

        <p className="text-center text-[11px] text-text-muted">
          Your data, your rules — everything is per-device and pseudonymous by design.
        </p>
      </div>
    </div>
  );
}
