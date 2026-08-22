"use client";
import { useQuery } from "@/lib/query";
import { api } from "@/lib/api";
import { Bell, CheckCircle, AlertCircle, Clock } from "lucide-react";
import { Dropdown } from "@/components/ui/Dropdown";
import { formatDuration } from "@/lib/format";

export function NotificationsBell() {
  const { data, mutate, isLoading } = useQuery("notifications", () => api.notifications.list(), { revalidateMs: 30_000 });
  return (
    <Dropdown
      trigger={<button className="relative p-1.5 rounded-lg text-text-mid hover:text-text-hi hover:bg-white/5" aria-label="Notifications"><Bell size={20} /><span className="absolute -top-1 -right-1 size-4 flex items-center justify-center text-[10px] font-bold bg-emergency text-bg rounded-full">{(data?.filter(n => n.status === "queued").length ?? 0) > 0 ? "•" : ""}</span></button>}
      items={[
        { label: isLoading ? "Loading…" : data?.length === 0 ? "No notifications" : "", onClick: () => {} },
        ...(data?.slice(0, 5).map((n, i) => ({
          label: "",
          onClick: () => {},
          icon: n.status === "sent" ? <CheckCircle size={14} className="text-safe" /> : n.status === "failed" ? <AlertCircle size={14} className="text-danger" /> : <Clock size={14} className="text-warn" />,
        })) ?? []),
        { label: "Mark all read", onClick: () => mutate() },
      ]}
    />
  );
}