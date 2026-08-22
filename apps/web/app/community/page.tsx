"use client";
import { useState } from "react";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Tabs } from "@/components/ui/Tabs";
import { timeAgo } from "@/lib/format";
import { Send, MessageSquare, Flag, CheckCircle, XCircle, MessageCircle, Users, Shield, AlertTriangle, X, ChevronDown } from "lucide-react";

function CommunityFeedContent({ filtered, tab, api }: { filtered: any[]; tab: string; api: any }) {
  return (
    <div className="space-y-3">
      {filtered.filter(p => tab === "verified" ? p.status === "VERIFIED" : p.status === "PENDING").map(p => (
        <Card key={p.id} variant="glass" className={`border-l-4 ${p.kind === "alert" ? "border-warn" : p.kind === "route_update" ? "border-accent" : "border-primary"}`}>
          <div className="flex items-start gap-3">
            <div className="size-10 rounded-xl bg-primary/20 flex items-center justify-center shrink-0">
              {p.kind === "alert" && <AlertTriangle size={20} className="text-warn" />}
              {p.kind === "route_update" && <Flag size={20} className="text-accent" />}
              {p.kind === "photo" && <MessageCircle size={20} className="text-primary" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant={p.status === "VERIFIED" ? "success" : "warn"}>{p.status}</Badge>
                <Badge variant="default">{p.kind}</Badge>
              </div>
              <p className="font-medium mt-1">{p.location}</p>
              <p className="text-sm text-text-mid mt-1">{p.text}</p>
              <div className="flex items-center gap-3 mt-2 text-xs text-text-low">
                <span>{p.created_at ? new Date(p.created_at).toLocaleString() : "Just now"}</span>
              </div>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

export default function CommunityPage() {
  const [filter, setFilter] = useState("");
  const { data: feed, mutate } = useQuery("community-feed", () => api.community.list(), { revalidateMs: 30_000 });
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<{ kind: "alert" | "route_update" | "photo"; location: string; text: string }>({ kind: "alert", location: "", text: "" });

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.location || !form.text) return;
    try {
      await api.community.create({ kind: form.kind, location: form.location, text: form.text });
      setShowCreate(false);
      setForm({ kind: "alert", location: "", text: "" });
      mutate();
    } catch { alert("Failed to post"); }
  };

  const filtered = feed?.posts?.filter(p => p.location.toLowerCase().includes(filter.toLowerCase()) || p.text.toLowerCase().includes(filter.toLowerCase())) ?? [];

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      <div className="p-4 sm:p-6 border-b border-line">
        <div className="mx-auto max-w-3xl flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-bold">Community Feed</h1>
            <p className="text-sm text-text-mid">Verified local updates. Posts are anonymous and moderated before appearing.</p>
          </div>
          <Button size="sm" onClick={() => setShowCreate(!showCreate)}><MessageSquare size={16} /> New Post</Button>
        </div>
        {showCreate && (
          <form onSubmit={create} className="mx-auto max-w-3xl p-4 border-t border-line glass animate-in space-y-3">
            <h3 className="font-medium">Share an Update</h3>
            <select className="px-4 py-2.5 bg-surface-elevated/50 border border-line rounded-xl text-text-hi focus:outline-none focus:ring-2 focus:ring-primary/40" value={form.kind} onChange={e => setForm(f => ({ ...f, kind: e.target.value as "alert" | "route_update" | "photo" }))}>
              <option value="alert">Safety Alert</option>
              <option value="route_update">Route Update</option>
              <option value="photo">Photo Report</option>
            </select>
            <Input label="Location" placeholder="e.g., Karol Bagh Metro" value={form.location} onChange={e => setForm(f => ({ ...f, location: e.target.value }))} required />
            <Input label="Details" placeholder="What happened? (10–280 chars)" value={form.text} onChange={e => setForm(f => ({ ...f, text: e.target.value }))} required />
            <div className="flex gap-2 pt-2">
              <Button type="submit">Post <Send size={16} /></Button>
              <Button type="button" variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            </div>
          </form>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="mx-auto max-w-3xl space-y-4">
          <input type="text" placeholder="Filter posts…" value={filter} onChange={e => setFilter(e.target.value)} className="w-full px-4 py-2.5 bg-surface-elevated/50 border border-line rounded-xl text-text-hi placeholder:text-text-low focus:outline-none focus:ring-2 focus:ring-primary/40 mb-4" />

          <Tabs defaultValue="verified" items={[
            { value: "verified", label: "Verified" },
            { value: "pending", label: "Pending Review" },
          ]} render={(tab) => (
            <CommunityFeedContent filtered={filtered} tab={tab} api={api} />
          )} />
        </div>
      </div>
    </div>
  );
}

function create(e: React.FormEvent) {
  e.preventDefault();
}