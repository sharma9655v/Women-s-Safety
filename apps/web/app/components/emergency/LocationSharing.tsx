"use client";

import { MapPin, Shield } from "lucide-react";
import { Card } from "@/app/components/ui/Card";

export function LocationSharing() {
  return (
    <Card className="border-info/20">
      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-info/15 text-info">
          <MapPin className="size-4" aria-hidden />
        </span>
        <div>
          <p className="text-sm font-semibold text-foreground">Share your location</p>
          <p className="mt-0.5 text-xs text-text-muted">
            Share your live location with trusted contacts. Location is encrypted and never stored
            on our servers.
          </p>
          <div className="mt-2 flex items-center gap-1.5 text-[10px] text-text-muted">
            <Shield className="size-3" aria-hidden />
            End-to-end encrypted · Explicit opt-in only
          </div>
        </div>
      </div>
    </Card>
  );
}
