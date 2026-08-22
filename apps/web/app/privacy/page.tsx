"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  MapPin,
  Plus,
  Shield,
  Timer,
  Trash2,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Badge } from "@/app/components/ui/Badge";
import { Button } from "@/app/components/ui/Button";
import { Card, CardHeader } from "@/app/components/ui/Card";
import {
  checkInGuardian,
  deleteContact,
  endEmergency,
  endGuardian,
  fetchActiveEmergency,
  fetchActiveGuardian,
  fetchActiveSharing,
  fetchContacts,
  fetchPrivacyDashboard,
  fetchPrivacySettings,
  startSharing,
  stopSharing,
  updateContact,
  updatePrivacySettings,
} from "@/lib/api";
import type {
  EmergencySession,
  GuardianSession,
  PrivacyDashboard,
  PrivacySettings,
  SharingSession,
  TrustedContact,
} from "@/lib/types";

const SHARING_TTL_S = 1800; // 30 minutes, within the backend max

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

function formatRemaining(expiresAt: string): string {
  const ms = Math.max(0, new Date(expiresAt).getTime() - Date.now());
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function formatElapsed(startedAt: string): string {
  const s = Math.max(0, Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000));
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

export default function PrivacyPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sharing, setSharing] = useState<SharingSession | null>(null);
  const [guardian, setGuardian] = useState<GuardianSession | null>(null);
  const [emergency, setEmergency] = useState<EmergencySession | null>(null);
  const [contacts, setContacts] = useState<TrustedContact[]>([]);
  const [settings, setSettings] = useState<PrivacySettings | null>(null);
  const [dashboard, setDashboard] = useState<PrivacyDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [, setTick] = useState(0);

  // The dashboard is the backend's own summary — separate fetch so its
  // failure never blocks the rest of the privacy center.
  useEffect(() => {
    let cancelled = false;
    fetchPrivacyDashboard()
      .then((d) => {
        if (!cancelled) setDashboard(d);
      })
      .catch((e) => {
        if (!cancelled) {
          setDashboardError(
            e instanceof Error && e.message ? e.message : "Unable to load the privacy dashboard.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setDashboardLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchActiveSharing().catch(() => null),
      fetchActiveGuardian().catch(() => null),
      fetchActiveEmergency().catch(() => null),
      fetchContacts().catch(() => [] as TrustedContact[]),
      fetchPrivacySettings().catch(() => null),
    ])
      .then(([s, g, e, c, p]) => {
        if (cancelled) return;
        setSharing(s);
        setGuardian(g);
        setEmergency(e);
        setContacts(c);
        setSettings(p);
      })
      .catch(() => {
        if (!cancelled) setError("Privacy data is unavailable right now.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Countdown tick while anything is active.
  useEffect(() => {
    if (!sharing && !guardian && !emergency) return;
    const t = setInterval(() => setTick((v) => v + 1), 1000);
    return () => clearInterval(t);
  }, [sharing, guardian, emergency]);

  const startLocationSharing = async () => {
    setBusy(true);
    setError(null);
    try {
      setSharing(await startSharing("GUARDIAN", SHARING_TTL_S, []));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start location sharing. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const stopLocationSharing = async () => {
    if (!sharing) return;
    setBusy(true);
    setError(null);
    try {
      await stopSharing(sharing.session_id);
      setSharing(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not stop location sharing. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const guardianCheckIn = async () => {
    if (!guardian) return;
    setBusy(true);
    setError(null);
    try {
      setGuardian(await checkInGuardian(guardian.session_id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not check in. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const guardianEnd = async () => {
    if (!guardian) return;
    setBusy(true);
    setError(null);
    try {
      await endGuardian(guardian.session_id, "cancelled");
      setGuardian(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not end the journey. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const emergencyEnd = async () => {
    if (!emergency) return;
    setBusy(true);
    setError(null);
    try {
      await endEmergency(emergency.session_id, "ended_by_user");
      setEmergency(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not end the emergency. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const toggleContact = async (c: TrustedContact) => {
    try {
      await updateContact(c.id, { enabled: !c.enabled });
      setContacts((prev) => prev.map((x) => (x.id === c.id ? { ...x, enabled: !x.enabled } : x)));
    } catch {
      setError("Could not update trusted contact.");
    }
  };

  const removeContact = async (c: TrustedContact) => {
    try {
      await deleteContact(c.id);
      setContacts((prev) => prev.filter((x) => x.id !== c.id));
    } catch {
      setError("Could not remove trusted contact.");
    }
  };

  const updateSetting = async <K extends keyof PrivacySettings>(
    key: K,
    value: PrivacySettings[K],
  ) => {
    if (!settings) return;
    const previous = settings;
    setSettings({ ...previous, [key]: value });
    try {
      setSettings(await updatePrivacySettings({ [key]: value }));
    } catch (e) {
      setSettings(previous);
      setError(e instanceof Error ? e.message : "Could not save the setting. Try again.");
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="glass max-w-md rounded-2xl p-8 text-center">
          <span className="mx-auto mb-3 flex size-12 items-center justify-center rounded-full bg-surface-hover text-text-muted">
            <Loader2 className="size-5 animate-spin" aria-hidden />
          </span>
          <p className="text-sm text-text-muted">Loading privacy dashboard…</p>
        </div>
      </div>
    );
  }

  const sharingActive = sharing?.status === "ACTIVE";
  const guardianActive = guardian?.status === "ACTIVE" || guardian?.status === "ESCALATED";
  const emergencyActive = emergency?.status === "ACTIVE";

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="privacy-page-wrap mx-auto max-w-3xl space-y-5">
        <header className="mb-2">
          <h1 className="text-xl font-bold text-foreground">
            <span className="text-primary">Privacy Center</span>
          </h1>
          <p className="mt-1 text-sm text-text-muted">
            Manage your data and safety features. All settings are per-device and pseudonymous —
            nothing is tied to your identity.
          </p>
        </header>

        {error ? (
          <p className="rounded-lg border border-danger/25 bg-danger/10 px-3 py-2 text-xs text-danger">
            {error}
          </p>
        ) : null}

        {/* Privacy dashboard — the backend's own summary */}
        <Card>
          <CardHeader
            title="Your data at a glance"
            subtitle="A summary computed by the backend for this device. Report history stays anonymous and is never listed here."
          />
          {dashboardLoading ? (
            <p className="flex items-center gap-2 py-2 text-xs text-text-muted">
              <Loader2 className="size-4 animate-spin" aria-hidden /> Loading dashboard…
            </p>
          ) : dashboardError ? (
            <p className="rounded-lg border border-warning/25 bg-warning/10 px-3 py-2 text-xs text-warning">
              Unable to load the privacy dashboard. {dashboardError}
            </p>
          ) : dashboard ? (
            <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <StatusRow
                label="Location sharing"
                value={dashboard.location_sharing_active ? "Active" : "Not active"}
                active={dashboard.location_sharing_active}
              />
              <StatusRow
                label="Guardian journey"
                value={
                  dashboard.guardian_active
                    ? dashboard.guardian_checkin_deadline
                      ? `Active · check-in due ${new Date(
                          dashboard.guardian_checkin_deadline,
                        ).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
                      : "Active"
                    : "Not active"
                }
                active={dashboard.guardian_active}
              />
              <StatusRow
                label="Emergency session"
                value={
                  dashboard.emergency_active
                    ? dashboard.emergency_notify_status === "sent"
                      ? "Active · contacts notified in-app"
                      : dashboard.emergency_notify_status === "queued"
                        ? "Active · notification queued"
                        : dashboard.emergency_notify_status === "failed"
                          ? "Active · notification failed"
                          : "Active"
                    : "Not active"
                }
                active={dashboard.emergency_active}
              />
              <StatusRow
                label="Voice guidance"
                value={dashboard.voice_guidance_active ? "Active" : "Not active"}
                active={dashboard.voice_guidance_active}
              />
              <StatusRow
                label="Discreet mode"
                value={dashboard.discreet_mode_enabled ? "On" : "Off"}
                active={dashboard.discreet_mode_enabled}
              />
              <StatusRow
                label="Trusted contacts"
                value={`${dashboard.trusted_contact_count}`}
                active={dashboard.trusted_contact_count > 0}
              />
              <StatusRow
                label="Voice language"
                value={dashboard.voice_language === "hi" ? "Hindi" : "English"}
                active={false}
              />
            </ul>
          ) : (
            <p className="py-2 text-xs text-text-muted">No dashboard data to show.</p>
          )}
        </Card>

        {/* Location Sharing */}
        <Card>
          <CardHeader
            title="Share your location"
            subtitle="Live location, shared only while you keep the session active."
            action={sharingActive ? <Badge tone="info">Active</Badge> : undefined}
          />
          <div className="flex items-start gap-3">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-info/15 text-info">
              <MapPin className="size-4" aria-hidden />
            </span>
            <div className="min-w-0 flex-1 space-y-2">
              {sharingActive && sharing ? (
                <>
                  <p className="text-sm text-foreground">
                    {sharing.latitude !== null && sharing.longitude !== null
                      ? `${sharing.latitude.toFixed(5)}, ${sharing.longitude.toFixed(5)}`
                      : "Waiting for a location fix…"}
                  </p>
                  <p className="flex items-center gap-1.5 text-xs text-text-muted">
                    <Timer className="size-3.5" aria-hidden />
                    Stops automatically in {formatRemaining(sharing.expires_at)}
                  </p>
                  <p className="flex items-center gap-1.5 text-[10px] text-text-muted">
                    <Shield className="size-3" aria-hidden />
                    Explicit opt-in only · always revocable
                  </p>
                  <Button
                    variant="danger"
                    size="sm"
                    loading={busy}
                    onClick={() => void stopLocationSharing()}
                  >
                    Stop sharing
                  </Button>
                </>
              ) : (
                <>
                  <p className="text-xs text-text-muted">
                    Your live location is sent to the backend and readable by your trusted contacts
                    while the session is active. It stops automatically after 30 minutes or when you
                    stop it.
                  </p>
                  <Button
                    variant="primary"
                    size="sm"
                    loading={busy}
                    onClick={() => void startLocationSharing()}
                  >
                    <MapPin className="size-3.5" aria-hidden /> Start sharing
                  </Button>
                </>
              )}
            </div>
          </div>
        </Card>

        {/* Guardian Mode */}
        <Card>
          <CardHeader
            title="Guardian mode"
            subtitle="Check in regularly while you travel; trusted contacts are notified only if you miss a check-in."
            action={
              guardianActive ? (
                guardian?.status === "ESCALATED" ? (
                  <Badge tone="danger">Escalated</Badge>
                ) : (
                  <Badge tone="success">Active</Badge>
                )
              ) : undefined
            }
          />
          <div className="flex items-start gap-3">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-success/15 text-success">
              <Shield className="size-4" aria-hidden />
            </span>
            <div className="min-w-0 flex-1 space-y-2">
              {guardianActive && guardian ? (
                <>
                  <p className="flex items-center gap-1.5 text-sm text-foreground">
                    <Timer className="size-3.5 text-success" aria-hidden />
                    Check-in due in{" "}
                    <span className="font-semibold">
                      {formatDeadline(guardian.checkin_deadline)}
                    </span>
                  </p>
                  {guardian.escalation_stage >= 1 ? (
                    <p className="rounded-lg border border-warning/25 bg-warning/10 px-2.5 py-2 text-xs text-warning">
                      {guardian.escalation_stage >= 2
                        ? "A check-in was missed and your trusted contacts were notified in-app. Delivery is not guaranteed — call for help if you are unsafe."
                        : "A check-in was missed. Your trusted contacts will be notified if you do not check in soon."}
                    </p>
                  ) : null}
                  {guardian.deviation_detected ? (
                    <p className="rounded-lg border border-warning/25 bg-warning/10 px-2.5 py-2 text-xs text-warning">
                      You are off your planned route. Your contacts have been notified in-app.
                    </p>
                  ) : null}
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="success"
                      size="sm"
                      loading={busy}
                      onClick={() => void guardianCheckIn()}
                    >
                      <CheckCircle2 className="size-3.5" aria-hidden /> Check in — I&apos;m okay
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      loading={busy}
                      onClick={() => void guardianEnd()}
                    >
                      End journey
                    </Button>
                  </div>
                </>
              ) : (
                <p className="text-xs text-text-muted">
                  No active guardian journey. Start one from the{" "}
                  <a href="/live" className="text-primary underline">
                    Map screen
                  </a>{" "}
                  by choosing trusted contacts and an expected arrival time.
                </p>
              )}
            </div>
          </div>
        </Card>

        {/* Emergency Sessions */}
        <Card>
          <CardHeader
            title="Emergency sessions"
            subtitle="Active and recent SOS sessions."
            action={emergencyActive ? <Badge tone="danger">Active</Badge> : undefined}
          />
          <div className="flex items-start gap-3">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-emergency/15 text-emergency">
              <AlertTriangle className="size-4" aria-hidden />
            </span>
            <div className="min-w-0 flex-1 space-y-2">
              {emergencyActive && emergency ? (
                <>
                  <p className="text-sm text-foreground">
                    {emergency.notified_contact_ids.length > 0
                      ? `${emergency.notified_contact_ids.length} trusted contact${emergency.notified_contact_ids.length !== 1 ? "s" : ""} selected for this session`
                      : "No trusted contacts selected for this session"}
                  </p>
                  <p className="flex items-center gap-1.5 text-xs text-text-muted">
                    <Timer className="size-3.5" aria-hidden />
                    Elapsed: {formatElapsed(emergency.started_at)}
                  </p>
                  <p className="flex items-center gap-1.5 text-[10px] text-text-muted">
                    {emergency.notify_status === "sent"
                      ? "Contacts were notified in-app."
                      : emergency.notify_status === "queued"
                        ? "Notification is queued — delivery is not yet confirmed."
                        : emergency.notify_status === "failed"
                          ? "Notification could not be delivered — call for help if you are unsafe."
                          : "No delivery channel is set up yet — call for help if you are unsafe."}
                  </p>
                  <Button
                    variant="danger"
                    size="sm"
                    loading={busy}
                    onClick={() => void emergencyEnd()}
                  >
                    End emergency
                  </Button>
                </>
              ) : (
                <p className="text-sm text-text-muted">No active emergency sessions.</p>
              )}
            </div>
          </div>
        </Card>

        {/* Trusted Contacts */}
        <Card>
          <CardHeader
            title="Trusted contacts"
            subtitle="People SOS and guardian mode can reach with your location."
            action={
              <a
                href="/contacts"
                className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-medium text-white transition-colors hover:bg-primary-hover"
              >
                <Plus className="size-3.5" aria-hidden /> Add contact
              </a>
            }
          />
          <div className="space-y-2">
            {contacts.length === 0 ? (
              <p className="text-sm text-text-muted">
                No trusted contacts yet. Add some so SOS and guardian mode can share your location.
              </p>
            ) : (
              <div className="grid gap-2 sm:grid-cols-2">
                {contacts.map((c) => (
                  <div
                    key={c.id}
                    className="flex items-center justify-between gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-xs"
                  >
                    <div className="min-w-0">
                      <p className="flex items-center gap-1.5 font-semibold text-foreground">
                        {c.name}
                        <Badge tone={c.role === "primary" ? "primary" : "default"}>{c.role}</Badge>
                      </p>
                      <p className="truncate text-[10px] text-text-muted">
                        {c.relationship} · {c.phone}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      <label className="flex cursor-pointer items-center gap-1.5 text-text-muted">
                        <input
                          type="checkbox"
                          checked={c.enabled}
                          onChange={() => void toggleContact(c)}
                          className="size-3.5 accent-primary"
                          aria-label={`Include ${c.name} in safety features`}
                        />
                        <span className="text-[10px]">Active</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => void removeContact(c)}
                        className="rounded-md p-1 text-text-muted transition-colors hover:bg-danger/10 hover:text-danger"
                        aria-label={`Remove ${c.name}`}
                      >
                        <Trash2 className="size-3.5" aria-hidden />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>

        {/* Privacy Settings */}
        <Card>
          <CardHeader title="Privacy settings" subtitle="Per-device preferences." />
          <div className="space-y-3">
            {settings ? (
              <>
                <div className="flex items-center justify-between min-h-[44px]">
                  <span className="text-sm text-text-secondary">Voice guidance</span>
                  <Switch
                    label="Voice guidance"
                    checked={settings.voice_guidance_enabled}
                    onChange={(v) => void updateSetting("voice_guidance_enabled", v)}
                  />
                </div>
                <div className="flex items-center justify-between min-h-[44px]">
                  <span className="text-sm text-text-secondary">Discreet mode</span>
                  <Switch
                    label="Discreet mode"
                    checked={settings.discreet_mode_enabled}
                    onChange={(v) => void updateSetting("discreet_mode_enabled", v)}
                  />
                </div>
                <div className="flex items-center justify-between min-h-[44px]">
                  <label htmlFor="privacy-voice-language" className="text-sm text-text-secondary">
                    Voice language
                  </label>
                  <select
                    id="privacy-voice-language"
                    value={settings.voice_language}
                    onChange={(e) => void updateSetting("voice_language", e.target.value)}
                    className="rounded-lg border border-border bg-surface px-2 py-1 text-xs text-foreground"
                  >
                    <option value="en">English</option>
                    <option value="hi">Hindi</option>
                  </select>
                </div>
              </>
            ) : (
              <p className="text-sm text-text-muted">Privacy settings unavailable.</p>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

function Switch({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative h-7 w-12 shrink-0 cursor-pointer rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 ${
        checked ? "bg-primary" : "bg-border"
      }`}
    >
      <span
        className={`absolute top-1 left-1 size-5 rounded-full bg-white shadow transition-transform ${
          checked ? "translate-x-5" : ""
        }`}
        aria-hidden
      />
    </button>
  );
}

function StatusRow({ label, value, active }: { label: string; value: string; active: boolean }) {
  return (
    <li className="flex items-center justify-between gap-3 rounded-xl border border-border bg-surface px-4 py-3 text-sm min-h-[44px]">
      <span className="text-text-muted">{label}</span>
      <span
        className={`flex items-center gap-1.5 font-medium ${
          active ? "text-success" : "text-text-secondary"
        }`}
      >
        <span
          className={`size-2 rounded-full ${active ? "bg-success" : "bg-text-muted"}`}
          aria-hidden
        />
        {value}
      </span>
    </li>
  );
}
