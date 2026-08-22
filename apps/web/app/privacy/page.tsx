"use client";
import { useState } from "react";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Tabs } from "@/components/ui/Tabs";
import { Switch } from "@/components/ui/Switch";
import { Shield, Eye, Lock, Database, Download, Trash2, Loader2, AlertTriangle, CheckCircle, User, Users, MapPin, Clock } from "lucide-react";
import { timeAgo } from "@/lib/format";

export default function PrivacyPage() {
  const { data: dashboard, mutate: mutateDash } = useQuery("privacy-dash", () => api.privacy.dashboard(), { revalidateMs: 30_000 });
  const { data: settings, mutate: mutateSettings } = useQuery("privacy-settings", () => api.privacy.settings.get(), { revalidateMs: 60_000 });
  const { data: notifications } = useQuery("notifications", () => api.notifications.list(), { revalidateMs: 30_000 });
  const [saving, setSaving] = useState(false);

  const updateSettings = async (updates: { voice_guidance_enabled?: boolean; voice_language?: string; discreet_mode_enabled?: boolean }) => {
    setSaving(true);
    try { await api.privacy.settings.update(updates); mutateSettings(); } catch { alert("Failed"); } finally { setSaving(false); }
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      <div className="p-4 sm:p-6 border-b border-line">
        <div className="mx-auto max-w-3xl">
          <h1 className="font-display text-2xl font-bold">Privacy Center</h1>
          <p className="text-sm text-text-mid">Control your data, sharing, and notifications. Your location is never tracked in the background.</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="mx-auto max-w-3xl space-y-6">
          {/* Active Status */}
          {dashboard && (
            <Card variant="glass">
              <h3 className="font-medium flex items-center gap-2 mb-4"><Shield size={20} className="text-primary" /> Active Safety Sessions</h3>
              <div className="grid gap-3 sm:grid-cols-2">
                <StatusItem label="Emergency SOS" active={dashboard.emergency_active} notify={dashboard.emergency_notify_status ?? undefined} icon={<AlertTriangle size={18} className="text-emergency" />} />
                <StatusItem label="Guardian Journey" active={dashboard.guardian_active} deadline={dashboard.guardian_checkin_deadline} icon={<Users size={18} className="text-primary" />} />
                <StatusItem label="Location Sharing" active={dashboard.location_sharing_active} expiry={dashboard.location_sharing_expires_at} icon={<MapPin size={18} className="text-accent" />} />
                <StatusItem label="Voice Guidance" active={dashboard.voice_guidance_active} lang={dashboard.voice_language} icon={<Clock size={18} className="text-info" />} />
              </div>
              <div className="mt-4 pt-4 border-t border-line">
                <p className="text-sm text-text-mid">Trusted contacts: <span className="font-medium text-text-hi">{dashboard.trusted_contact_count}</span></p>
              </div>
            </Card>
          )}

          {/* Settings */}
          <Tabs defaultValue="sharing" items={[
            { value: "sharing", label: "Location Sharing" },
            { value: "voice", label: "Voice Guidance" },
            { value: "discreet", label: "Discreet Mode" },
            { value: "data", label: "Your Data" },
          ]}>
            {(tab) => (
              <Card variant="glass">
                <h3 className="font-medium mb-4">{tab === "sharing" && "Location Sharing"} {tab === "voice" && "Voice Guidance"} {tab === "discreet" && "Discreet Mode"} {tab === "data" && "Your Data"}</h3>

                {tab === "sharing" && settings && (
                  <form onSubmit={e => { e.preventDefault(); updateSettings({ discreet_mode_enabled: (e.target as HTMLFormElement).discreet_mode_enabled?.checked }); }} className="space-y-4">
                    <label className="flex items-center justify-between">
                      <div className="flex items-center gap-3"><MapPin size={20} className="text-accent" /><span>Location sharing enabled</span></div>
                      <Switch checked={settings.discreet_mode_enabled} name="discreet_mode_enabled" onChange={e => updateSettings({ discreet_mode_enabled: e.target.checked })} />
                    </label>
                    <p className="text-sm text-text-mid">When enabled, trusted contacts can see your real-time location during active sessions.</p>
                  </form>
                )}

                {tab === "voice" && settings && (
                  <form onSubmit={e => { e.preventDefault(); updateSettings({ voice_guidance_enabled: (e.target as HTMLFormElement).voice_guidance_enabled?.checked, voice_language: (e.target as HTMLFormElement).voice_language?.value }); }} className="space-y-4">
                    <label className="flex items-center justify-between">
                      <div className="flex items-center gap-3"><Shield size={20} className="text-info" /><span>Voice guidance</span></div>
                      <Switch checked={settings.voice_guidance_enabled} name="voice_guidance_enabled" onChange={e => updateSettings({ voice_guidance_enabled: e.target.checked })} />
                    </label>
                    <select name="voice_language" defaultValue={settings.voice_language} className="w-full px-4 py-2.5 bg-surface-elevated/50 border border-line rounded-xl text-text-hi focus:outline-none focus:ring-2 focus:ring-primary/40">
                      <option value="en">English</option>
                      <option value="hi">Hindi</option>
                      <option value="mr">Marathi</option>
                    </select>
                    <Button type="submit" className="w-full" disabled={saving}>{saving ? <Loader2 size={18} className="animate-spin" /> : "Save Voice Settings"}</Button>
                  </form>
                )}

                {tab === "discreet" && (
                  <div className="space-y-4">
                    <p className="text-sm text-text-mid">Discreet mode settings are managed in Profile → Discreet.</p>
                    <Button variant="outline">Open Profile Settings</Button>
                  </div>
                )}

                {tab === "data" && (
                  <div className="space-y-4">
                    <div className="glass p-4 rounded-xl space-y-2">
                      <h4 className="font-medium">Data We Store</h4>
                      <ul className="space-y-1 text-sm text-text-mid">
                        <li>• Pseudonymous device ID (hashed, no personal info)</li>
                        <li>• Emergency session history (30 days, auto-deleted)</li>
                        <li>• Guardian/journey sessions (duration of session)</li>
                        <li>• Trusted contacts (encrypted, you control)</li>
                        <li>• Safety preferences (local + synced)</li>
                      </ul>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="outline"><Download size={16} /> Export My Data</Button>
                      <Button variant="danger"><Trash2 size={16} /> Delete Account</Button>
                    </div>
                  </div>
                )}
              </Card>
            )}
          </Tabs>

          {/* Notifications */}
          <Card variant="glass">
            <h3 className="font-medium flex items-center gap-2 mb-4"><Shield size={20} className="text-info" /> Recent Notifications</h3>
            {notifications?.length === 0 ? (
              <p className="text-text-mid text-center py-8">No notifications yet</p>
            ) : (
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {notifications?.slice(0, 20).map(n => (
                  <div key={n.id} className="glass p-3 rounded-xl flex items-start gap-3">
                    <div className="size-8 rounded-lg bg-primary/20 flex items-center justify-center shrink-0"><CheckCircle size={16} className="text-safe" /></div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm">{n.type}</p>
                      <p className="text-xs text-text-mid">Channel: {n.channel} • Status: {n.status}</p>
                      <p className="text-xs text-text-low mt-1">{timeAgo(n.created_at)}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Transparency */}
          <Card variant="glass" className="border-primary/20">
            <h3 className="font-medium flex items-center gap-2 mb-4"><Shield size={20} className="text-primary" /> Transparency Commitment</h3>
            <ul className="space-y-2 text-sm text-text-mid">
              <li className="flex items-center gap-2"><CheckCircle size={16} className="text-safe" /> No background location tracking</li>
              <li className="flex items-center gap-2"><CheckCircle size={16} className="text-safe" /> Device ID is pseudonymous (hashed)</li>
              <li className="flex items-center gap-2"><CheckCircle size={16} className="text-safe" /> Emergency contacts only see location during active sessions</li>
              <li className="flex items-center gap-2"><CheckCircle size={16} className="text-safe" /> Report history is anonymous by design</li>
              <li className="flex items-center gap-2"><CheckCircle size={16} className="text-safe" /> All data encrypted at rest and in transit</li>
              <li className="flex items-center gap-2"><CheckCircle size={16} className="text-safe" /> Open-source risk models — see /models page</li>
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
}

function StatusItem({ label, active, notify, deadline, expiry, lang, icon }: { label: string; active: boolean; notify?: string; deadline?: string | null; expiry?: string | null; lang?: string; icon: React.ReactNode }) {
  return (
    <div className="glass p-3 rounded-xl flex items-center gap-3">
      <div className={`size-10 rounded-xl flex items-center justify-center ${active ? "bg-emergency/20" : "bg-surface-elevated/50"}`}>{icon}</div>
      <div className="flex-1 min-w-0">
        <p className="font-medium">{label}</p>
        <p className="text-xs text-text-mid">{active ? "ACTIVE" : "Inactive"}{notify ? ` • ${notify}` : ""}{deadline ? ` • Check-in: ${deadline}` : ""}{expiry ? ` • Expires: ${expiry}` : ""}{lang ? ` • ${lang}` : ""}</p>
      </div>
      <span className={`size-3 rounded-full ${active ? "bg-emergency animate-pulse" : "bg-line"}`} />
    </div>
  );
}