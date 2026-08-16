"use client";

import { Bell, BellOff, Loader2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { IconButton } from "@/app/components/ui/IconButton";
import { fetchNotifications } from "@/lib/api";
import type { NotificationEvent } from "@/lib/types";

const TYPE_LABELS: Record<string, string> = {
  sos_started: "SOS started",
  sos_ended: "SOS ended",
  location_sharing_started: "Location sharing started",
  location_sharing_stopped: "Location sharing stopped",
};

function statusLabel(status: string): string {
  switch (status) {
    case "queued":
      return "Queued for delivery";
    case "sent":
      return "Delivered";
    case "failed":
      return "Delivery failed";
    default:
      return "No channel configured — not delivered";
  }
}

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const min = Math.floor(ms / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const [events, setEvents] = useState<NotificationEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);

  const load = useCallback(() => {
    fetchNotifications(8)
      .then(setEvents)
      .catch(() => setError("Notifications are unavailable right now."));
  }, []);

  useEffect(() => {
    if (!open) return;
    load();
  }, [open, load]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const count = events?.length ?? 0;

  return (
    <div ref={panelRef} className="relative">
      <IconButton
        label={`Notifications${count > 0 ? ` (${count})` : ""}`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="relative">
          <Bell className="size-4" aria-hidden />
          {count > 0 ? (
            <span className="absolute -top-1.5 -right-1.5 flex size-3.5 items-center justify-center rounded-full bg-emergency text-[8px] font-bold text-white">
              {count}
            </span>
          ) : null}
        </span>
      </IconButton>

      {open ? (
        <div className="glass-strong absolute top-full right-0 z-50 mt-2 w-[320px] overflow-hidden rounded-xl shadow-2xl">
          <p className="border-b border-border px-3 py-2 text-xs font-semibold text-foreground">
            Notifications
          </p>
          <div className="max-h-80 overflow-y-auto">
            {error ? (
              <p className="px-3 py-3 text-xs text-danger">{error}</p>
            ) : events === null ? (
              <div className="flex items-center gap-2 px-3 py-3 text-xs text-text-muted">
                <Loader2 className="size-3.5 animate-spin" aria-hidden /> Loading…
              </div>
            ) : events.length === 0 ? (
              <p className="flex items-center gap-2 px-3 py-3 text-xs text-text-muted">
                <BellOff className="size-3.5" aria-hidden /> No events yet
              </p>
            ) : (
              <ul>
                {events.map((e) => (
                  <li key={e.id} className="border-b border-border/60 px-3 py-2.5 last:border-0">
                    <p className="text-xs font-medium text-foreground">
                      {TYPE_LABELS[e.type] ?? e.type}
                    </p>
                    <p className="mt-0.5 text-[11px] text-text-muted">{statusLabel(e.status)}</p>
                    <p className="mt-0.5 text-[10px] text-text-muted">{timeAgo(e.created_at)}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
