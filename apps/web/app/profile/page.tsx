"use client";
import { useState } from "react";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Tabs } from "@/components/ui/Tabs";
import { Switch } from "@/components/ui/Switch";
import { Shield, Bell, Eye, User, Key, Loader2, Palette, Globe, Save, Edit, LogOut, Smartphone } from "lucide-react";

export default function ProfilePage() {
  const { data: prefs, mutate: mutatePrefs } = useQuery("prefs", () => api.preferences.get(), { revalidateMs: 60_000 });
  const { data: discreet, mutate: mutateDiscreet } = useQuery("discreet", () => api.discreet.get(), { revalidateMs: 60_000 });
  const [saving, setSaving] = useState(false);
  const [deviceToken, setDeviceToken] = useState("");

  const savePrefs = async (updates: import("@/lib/types").SafetyPreferencesUpdate) => {
    setSaving(true);
    try { await api.preferences.update(updates); mutatePrefs(); } catch { alert("Failed"); } finally { setSaving(false); }
  };
  const saveDiscreet = async (updates: import("@/lib/types").DiscreetModeSettingsUpdate) => {
    setSaving(true);
    try { await api.discreet.update(updates); mutateDiscreet(); } catch { alert("Failed"); } finally { setSaving(false); }
  };
  const refreshToken = async () => { try { const t = await api.acquireToken(); setDeviceToken(t); } catch {} };

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      <div className="p-4 sm:p-6 border-b border-line">
        <div className="mx-auto max-w-2xl">
          <h1 className="font-display text-2xl font-bold">Profile & Settings</h1>
          <p className="text-sm text-text-mid">Device identity, safety preferences, discreet mode, and privacy.</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="mx-auto max-w-2xl space-y-6">
          {/* Device Identity */}
          <Card variant="glass">
            <h3 className="font-medium flex items-center gap-2 mb-4"><Smartphone size={20} className="text-accent" /> Device Identity</h3>
            <div className="space-y-3">
              <div className="glass p-3 rounded-xl"><span className="text-xs text-text-mid">Client ID</span><p className="font-mono text-sm text-text-hi break-all">{deviceToken || "Loading…"}</p></div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={refreshToken}><Loader2 size={16} /> Refresh Token</Button>
              </div>
            </div>
          </Card>

          <Tabs defaultValue="safety" items={[
            { value: "safety", label: "Safety" },
            { value: "discreet", label: "Discreet" },
            { value: "notifications", label: "Notify" },
            { value: "privacy", label: "Privacy" },
          ]}>
            {(tab) => (
              <Card variant="glass">
                <h3 className="font-medium mb-4">{tab === "safety" && "Safety Preferences"} {tab === "discreet" && "Discreet Mode"} {tab === "notifications" && "Notifications"} {tab === "privacy" && "Privacy Settings"}</h3>

                {tab === "safety" && prefs && (
                  <form onSubmit={e => { e.preventDefault(); savePrefs({
                    prefer_better_lit: (e.target as HTMLFormElement).prefer_better_lit?.checked,
                    prefer_main_roads: (e.target as HTMLFormElement).prefer_main_roads?.checked,
                    prefer_near_emergency: (e.target as HTMLFormElement).prefer_near_emergency?.checked,
                    avoid_known_hazards: (e.target as HTMLFormElement).avoid_known_hazards?.checked,
                    avoid_isolated_roads: (e.target as HTMLFormElement).avoid_isolated_roads?.checked,
                    minimize_walking_time: (e.target as HTMLFormElement).minimize_walking_time?.checked,
                    default_profile: (e.target as HTMLFormElement).default_profile?.value as any,
                  }); }} className="space-y-4">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <label className="flex items-center gap-2 cursor-pointer"><Switch checked={prefs.prefer_better_lit} name="prefer_better_lit" /><span className="text-sm">Prefer better-lit routes</span></label>
                      <label className="flex items-center gap-2 cursor-pointer"><Switch checked={prefs.prefer_main_roads} name="prefer_main_roads" /><span className="text-sm">Prefer main roads</span></label>
                      <label className="flex items-center gap-2 cursor-pointer"><Switch checked={prefs.prefer_near_emergency} name="prefer_near_emergency" /><span className="text-sm">Prefer near emergency services</span></label>
                      <label className="flex items-center gap-2 cursor-pointer"><Switch checked={prefs.avoid_known_hazards} name="avoid_known_hazards" /><span className="text-sm">Avoid known hazards</span></label>
                      <label className="flex items-center gap-2 cursor-pointer"><Switch checked={prefs.avoid_isolated_roads} name="avoid_isolated_roads" /><span className="text-sm">Avoid isolated roads</span></label>
                      <label className="flex items-center gap-2 cursor-pointer"><Switch checked={prefs.minimize_walking_time} name="minimize_walking_time" /><span className="text-sm">Minimize walking time</span></label>
                    </div>
                    <div>
                      <label className="block text-sm text-text-mid mb-2">Default routing profile</label>
                      <select name="default_profile" defaultValue={prefs.default_profile} className="w-full px-4 py-2.5 bg-surface-elevated/50 border border-line rounded-xl text-text-hi focus:outline-none focus:ring-2 focus:ring-primary/40">
                        <option value="safety">Safety First</option>
                        <option value="balanced">Balanced</option>
                        <option value="time">Fastest</option>
                      </select>
                    </div>
                    <Button type="submit" className="w-full" disabled={saving}>{saving ? <Loader2 size={18} className="animate-spin" /> : <>Save Preferences <Save size={16} /></>}</Button>
                  </form>
                )}

                {tab === "discreet" && discreet && (
                  <form onSubmit={e => { e.preventDefault(); saveDiscreet({
                    enabled: (e.target as HTMLFormElement).enabled?.checked,
                    quick_sos_gesture: (e.target as HTMLFormElement).quick_sos_gesture?.value,
                    exit_to_neutral_app: (e.target as HTMLFormElement).exit_to_neutral_app?.checked,
                    neutral_app_label: (e.target as HTMLFormElement).neutral_app_label?.value,
                    neutral_app_icon: (e.target as HTMLFormElement).neutral_app_icon?.value,
                  }); }} className="space-y-4">
                    <label className="flex items-center gap-2 cursor-pointer"><Switch checked={discreet.enabled} name="enabled" /><span className="text-sm">Enable Discreet Mode</span></label>
                    <Input label="Quick SOS Gesture" placeholder="e.g., triple-tap power" name="quick_sos_gesture" defaultValue={discreet.quick_sos_gesture} />
                    <label className="flex items-center gap-2 cursor-pointer"><Switch checked={discreet.exit_to_neutral_app} name="exit_to_neutral_app" /><span className="text-sm">Exit to neutral app on close</span></label>
                    <Input label="Neutral App Label" placeholder="e.g., Weather" name="neutral_app_label" defaultValue={discreet.neutral_app_label} />
                    <Input label="Neutral App Icon" placeholder="emoji or identifier" name="neutral_app_icon" defaultValue={discreet.neutral_app_icon} />
                    <Button type="submit" className="w-full" disabled={saving}>{saving ? <Loader2 size={18} className="animate-spin" /> : <>Save Discreet Settings <Save size={16} /></>}</Button>
                  </form>
                )}

                {tab === "notifications" && (
                  <div className="space-y-4">
                    <label className="flex items-center gap-2 cursor-pointer"><Switch checked={prefs?.voice_guidance_enabled} onChange={e => savePrefs({ voice_guidance_enabled: e.target.checked })} /><span className="text-sm">Voice guidance enabled</span></label>
                    <Input label="Voice Language" placeholder="e.g., en, hi, mr" defaultValue={prefs?.voice_language} onChange={e => savePrefs({ voice_language: e.target.value })} />
                  </div>
                )}

                {tab === "privacy" && (
                  <div className="space-y-4">
                    <p className="text-sm text-text-mid">Privacy settings are managed in the dedicated Privacy page.</p>
                    <Button variant="outline">Open Privacy Center <Shield size={16} /></Button>
                  </div>
                )}
              </Card>
            )}
          </Tabs>

          {/* Sign out */}
          <Card variant="glass" className="border-emergency/30">
            <Button variant="danger" className="w-full" onClick={() => { /* sign out logic */ }}><LogOut size={18} /> Sign Out</Button>
          </Card>
        </div>
      </div>
    </div>
  );
}