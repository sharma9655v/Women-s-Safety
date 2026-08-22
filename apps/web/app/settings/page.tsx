"use client";

import { Check, EyeOff, Loader2, Route as RouteIcon, Volume2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/app/components/ui/Badge";
import { Button } from "@/app/components/ui/Button";
import { Card, CardHeader } from "@/app/components/ui/Card";
import { Input } from "@/app/components/ui/Input";
import {
  fetchDiscreetMode,
  fetchPreferences,
  updateDiscreetMode,
  updatePreferences,
} from "@/lib/api";
import type { DiscreetModeSettings, SafetyPreference, SafetyPreferences } from "@/lib/types";

const PROFILES: { id: SafetyPreference; label: string; detail: string }[] = [
  {
    id: "safety",
    label: "Safety Priority",
    detail: "Routes weighted toward lower estimated risk, even if slower.",
  },
  {
    id: "balanced",
    label: "Balanced",
    detail: "A mix of safety, distance and time — the default.",
  },
  {
    id: "time",
    label: "Time Priority",
    detail: "Fastest routes first; risk still shown, never hidden.",
  },
];

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

const TOGGLE_FIELDS: { key: keyof SafetyPreferences; label: string; detail: string }[] = [
  { key: "prefer_better_lit", label: "Prefer better-lit roads", detail: "When evidence exists." },
  {
    key: "prefer_main_roads",
    label: "Prefer main roads",
    detail: "Busier roads with more activity.",
  },
  {
    key: "prefer_near_emergency",
    label: "Stay near emergency facilities",
    detail: "Police stations, hospitals, transit.",
  },
  {
    key: "avoid_known_hazards",
    label: "Avoid known hazard areas",
    detail: "Based on verified reports only.",
  },
  {
    key: "avoid_isolated_roads",
    label: "Avoid isolated roads",
    detail: "Low-activity stretches when avoidable.",
  },
  { key: "minimize_walking_time", label: "Minimize walking time", detail: "For transit modes." },
];

export default function SettingsPage() {
  const [prefs, setPrefs] = useState<SafetyPreferences | null>(null);
  const [discreet, setDiscreet] = useState<DiscreetModeSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchPreferences().catch(() => null), fetchDiscreetMode().catch(() => null)])
      .then(([p, d]) => {
        if (cancelled) return;
        setPrefs(p);
        setDiscreet(d);
      })
      .catch(() => {
        if (!cancelled) setError("Settings are unavailable right now.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const savePreferences = useCallback(async () => {
    if (!prefs) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updatePreferences(prefs);
      setPrefs(updated);
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save preferences. Try again.");
    } finally {
      setSaving(false);
    }
  }, [prefs]);

  const togglePref = (key: keyof SafetyPreferences) => {
    if (!prefs) return;
    setPrefs({ ...prefs, [key]: !prefs[key] });
  };

  const saveDiscreet = useCallback(
    async (patch: Partial<DiscreetModeSettings>) => {
      if (!discreet) return;
      const optimistic = { ...discreet, ...patch };
      setDiscreet(optimistic);
      setError(null);
      try {
        setDiscreet(await updateDiscreetMode(optimistic));
      } catch (e) {
        setDiscreet(discreet);
        setError(e instanceof Error ? e.message : "Could not save discreet mode settings.");
      }
    },
    [discreet],
  );

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="glass max-w-md rounded-2xl p-8 text-center">
          <Loader2 className="mx-auto mb-3 size-6 animate-spin text-primary" aria-hidden />
          <p className="text-sm text-text-muted">Loading settings…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="settings-page-wrap mx-auto max-w-3xl space-y-5 p-4 lg:p-6">
        <header>
          <h1 className="text-xl font-bold text-foreground">
            <span className="text-primary">Settings</span>
          </h1>
          <p className="mt-1 text-sm text-text-muted">
            Per-device preferences that influence routing — they never bypass the safety model.
          </p>
        </header>

        {error ? (
          <p className="rounded-lg border border-danger/25 bg-danger/10 px-3 py-2 text-xs text-danger">
            {error}
          </p>
        ) : null}

        {prefs ? (
          <Card>
            <CardHeader
              title="Route preferences"
              subtitle="How routes are weighted when multiple options exist."
              action={saved ? <Badge tone="success">Saved</Badge> : undefined}
            />
            <div className="space-y-3">
              <p className="text-xs font-semibold text-text-muted uppercase tracking-wide">
                Default profile
              </p>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                {PROFILES.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() =>
                      setPrefs({ ...prefs, default_profile: p.id as SafetyPreference })
                    }
                    aria-pressed={prefs.default_profile === p.id}
                    className={`cursor-pointer rounded-xl border p-4 text-left transition-colors ${
                      prefs.default_profile === p.id
                        ? "border-primary/40 bg-primary/8"
                        : "border-border bg-surface hover:border-primary/25"
                    }`}
                  >
                    <span className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
                      <RouteIcon className="size-3.5 text-primary" aria-hidden />
                      {p.label}
                      {prefs.default_profile === p.id ? (
                        <Check className="size-3.5 text-primary" aria-hidden />
                      ) : null}
                    </span>
                    <span className="mt-1 block text-xs text-text-muted">{p.detail}</span>
                  </button>
                ))}
              </div>

              <div className="space-y-2.5 border-t border-border pt-3">
                {TOGGLE_FIELDS.map((f) => (
                  <div key={f.key} className="flex items-center justify-between gap-4 min-h-[44px]">
                    <div className="min-w-0">
                      <p className="text-sm text-text-secondary">{f.label}</p>
                      <p className="text-xs text-text-muted">{f.detail}</p>
                    </div>
                    <Switch
                      label={f.label}
                      checked={prefs[f.key] as boolean}
                      onChange={() => togglePref(f.key)}
                    />
                  </div>
                ))}
              </div>

              <Button loading={saving} onClick={() => void savePreferences()}>
                Save preferences
              </Button>
            </div>
          </Card>
        ) : null}

        {discreet ? (
          <Card>
            <CardHeader
              title="Discreet mode"
              subtitle="Make the app look like a neutral utility when you are in a risky situation."
              action={discreet.enabled ? <Badge tone="warning">Active</Badge> : undefined}
            />
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="flex items-center gap-1.5 text-sm text-text-secondary">
                    <EyeOff className="size-4 text-primary" aria-hidden /> Discreet mode
                  </p>
                  <p className="text-[11px] text-text-muted">
                    Branding is hidden behind a neutral label while enabled.
                  </p>
                </div>
                <Switch
                  label="Discreet mode"
                  checked={discreet.enabled}
                  onChange={(v) => void saveDiscreet({ enabled: v })}
                />
              </div>

              {discreet.enabled ? (
                <>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <Input
                      id="neutral-label"
                      label="Neutral app name"
                      value={discreet.neutral_app_label}
                      maxLength={20}
                      onChange={(e) => void saveDiscreet({ neutral_app_label: e.target.value })}
                    />
                    <Input
                      id="neutral-icon"
                      label="Neutral app icon"
                      value={discreet.neutral_app_icon}
                      maxLength={20}
                      onChange={(e) => void saveDiscreet({ neutral_app_icon: e.target.value })}
                    />
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm text-text-secondary">Exit to neutral app</p>
                    <Switch
                      label="Exit to neutral app"
                      checked={discreet.exit_to_neutral_app}
                      onChange={(v) => void saveDiscreet({ exit_to_neutral_app: v })}
                    />
                  </div>
                </>
              ) : null}
            </div>
          </Card>
        ) : null}

        {prefs ? (
          <Card>
            <CardHeader
              title="Voice guidance"
              subtitle="Spoken safety cues while navigating (web voices, not guaranteed)."
            />
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <p className="flex items-center gap-1.5 text-sm text-text-secondary">
                  <Volume2 className="size-4 text-primary" aria-hidden /> Voice guidance
                </p>
                <Switch
                  label="Voice guidance"
                  checked={prefs.voice_guidance_enabled}
                  onChange={(v) => setPrefs({ ...prefs, voice_guidance_enabled: v })}
                />
              </div>
              <div className="flex items-center justify-between gap-3">
                <label htmlFor="voice-language" className="text-sm text-text-secondary">
                  Voice language
                </label>
                <select
                  id="voice-language"
                  value={prefs.voice_language}
                  onChange={(e) => setPrefs({ ...prefs, voice_language: e.target.value })}
                  className="rounded-lg border border-border bg-surface px-2 py-1 text-xs text-foreground"
                >
                  <option value="en">English</option>
                  <option value="hi">Hindi</option>
                </select>
              </div>
              <Button loading={saving} onClick={() => void savePreferences()}>
                Save voice settings
              </Button>
            </div>
          </Card>
        ) : null}
      </div>
    </div>
  );
}
