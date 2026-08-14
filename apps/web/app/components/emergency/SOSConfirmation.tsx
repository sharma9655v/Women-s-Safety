"use client";

import { AlertTriangle, Copy, Link2, Loader2, MapPin, Phone, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/app/components/ui/Button";
import { Modal } from "@/app/components/ui/Modal";

const CONTACTS = [
  { label: "Women Helpline", number: "181", detail: "24×7 free helpline" },
  { label: "Police", number: "112", detail: "Emergency services" },
  { label: "Ambulance", number: "102", detail: "Medical emergency" },
];

type LocationState =
  | { status: "idle" }
  | { status: "locating" }
  | { status: "ready"; lat: number; lon: number; mapsUrl: string }
  | { status: "error"; message: string };

function formatCoords(lat: number, lon: number): string {
  return `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
}

export function SOSConfirmation({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [location, setLocation] = useState<LocationState>({ status: "idle" });
  const [copied, setCopied] = useState(false);

  const locate = () => {
    if (!("geolocation" in navigator)) {
      setLocation({
        status: "error",
        message: "Location sharing is not supported by this browser.",
      });
      return;
    }
    setLocation({ status: "locating" });
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        setLocation({
          status: "ready",
          lat,
          lon,
          mapsUrl: `https://www.google.com/maps?q=${lat},${lon}`,
        });
      },
      (err) => {
        setLocation({
          status: "error",
          message:
            err.code === err.PERMISSION_DENIED
              ? "Location permission was denied."
              : "Could not determine your location right now.",
        });
      },
      { enableHighAccuracy: true, timeout: 8000 },
    );
  };

  const copyLink = async () => {
    if (location.status !== "ready") return;
    await navigator.clipboard.writeText(location.mapsUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const share = async () => {
    if (location.status !== "ready") return;
    const text = `I'm sharing my live location. Map: ${location.mapsUrl} (${formatCoords(location.lat, location.lon)})`;
    if (navigator.share) {
      try {
        await navigator.share({ title: "Live location", text, url: location.mapsUrl });
      } catch {
        copyLink();
      }
    } else {
      copyLink();
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Emergency">
      <div className="space-y-4">
        <div className="flex flex-col items-center gap-3 py-2 text-center">
          <span className="flex size-16 items-center justify-center rounded-full bg-emergency/15 text-emergency animate-ring-pulse">
            <AlertTriangle className="size-7" aria-hidden />
          </span>
          <p className="text-sm text-text-secondary">
            Call emergency services or share your location with trusted contacts.
          </p>
        </div>

        <div className="space-y-2">
          {CONTACTS.map((c) => (
            <a
              key={c.number}
              href={`tel:${c.number}`}
              className="flex items-center gap-3 rounded-xl border border-border bg-surface p-3 transition-colors hover:border-emergency/30 hover:bg-emergency/5"
            >
              <Phone className="size-4 text-emergency" aria-hidden />
              <div className="flex-1">
                <p className="text-sm font-semibold text-foreground">{c.label}</p>
                <p className="text-xs text-text-muted">{c.detail}</p>
              </div>
              <span className="text-sm font-bold text-emergency">{c.number}</span>
            </a>
          ))}
        </div>

        <div className="rounded-xl border border-border bg-surface/60 p-3">
          {location.status === "idle" ? (
            <button
              type="button"
              onClick={locate}
              className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm font-medium text-primary transition-colors hover:bg-primary/5"
            >
              <MapPin className="size-4" aria-hidden /> Share live location
            </button>
          ) : null}

          {location.status === "locating" ? (
            <div className="flex items-center gap-2 px-2 py-1.5 text-sm text-text-secondary">
              <Loader2 className="size-4 animate-spin" aria-hidden /> Getting your location…
            </div>
          ) : null}

          {location.status === "error" ? (
            <div className="flex items-center justify-between gap-2 px-2 py-1.5 text-sm text-danger">
              <span>{location.message}</span>
              <button
                type="button"
                onClick={locate}
                className="text-xs font-medium text-primary underline"
              >
                Try again
              </button>
            </div>
          ) : null}

          {location.status === "ready" ? (
            <div className="space-y-2">
              <p className="flex items-center gap-2 px-2 text-sm font-medium text-foreground">
                <MapPin className="size-4 text-success" aria-hidden />
                {formatCoords(location.lat, location.lon)}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button variant="danger" size="sm" onClick={share}>
                  <Link2 className="size-3.5" aria-hidden /> Share link
                </Button>
                <Button variant="secondary" size="sm" onClick={copyLink}>
                  <Copy className="size-3.5" aria-hidden />
                  {copied ? "Copied" : "Copy"}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs"
                  onClick={() => window.open(location.mapsUrl, "_blank", "noopener")}
                >
                  <Link2 className="size-3.5" aria-hidden /> Open map
                </Button>
              </div>
            </div>
          ) : null}
        </div>

        <Button variant="secondary" fullWidth onClick={onClose}>
          <X className="size-4" aria-hidden /> Cancel
        </Button>
      </div>
    </Modal>
  );
}
