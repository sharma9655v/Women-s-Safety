"use client";

import {
  Car,
  Crosshair,
  Footprints,
  MapPin,
  Route as RouteIcon,
  Share2,
  Shield,
  ShieldCheck,
  Train,
  X,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useState } from "react";
import type { ConfidenceLevel, SafetyBand, SafetyPreference } from "@/lib/types";
import { LiveStatusSection } from "./LiveStatusSection";
import { QuickActionsGrid } from "./QuickActionsGrid";

/* ------------------------------------------------------------------ */
/* Transport mode selector (inline, matching reference design)         */
/* ------------------------------------------------------------------ */

const MODES = [
  { id: "walking", icon: Footprints, label: "Walk" },
  { id: "car", icon: Car, label: "Car" },
  { id: "transit", icon: Train, label: "Transit" },
];

function TransportModePicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex gap-1 rounded-xl border border-border bg-surface p-1">
      {MODES.map((m) => {
        const Icon = m.icon;
        const active = value === m.id;
        return (
          <button
            key={m.id}
            type="button"
            onClick={() => onChange(m.id)}
            aria-pressed={active}
            className={`flex flex-1 min-h-10 cursor-pointer items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium transition-all duration-200 select-none ${
              active
                ? "bg-primary text-white shadow-sm"
                : "text-text-muted hover:bg-surface-hover hover:text-foreground"
            }`}
          >
            <Icon className="size-4" aria-hidden />
            <span>{m.label}</span>
          </button>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Safety preference selector (matching reference design)              */
/* ------------------------------------------------------------------ */

const PREFERENCES: { id: SafetyPreference; label: string; detail: string; icon: typeof Shield }[] =
  [
    {
      id: "safety",
      label: "Safety Priority",
      detail: "Estimated lower risk, may take longer",
      icon: Shield,
    },
    {
      id: "balanced",
      label: "Balanced",
      detail: "Best balance of estimated safety & time",
      icon: RouteIcon,
    },
    {
      id: "time",
      label: "Time Priority",
      detail: "Faster but may have higher estimated risk",
      icon: Footprints,
    },
  ];

/* ------------------------------------------------------------------ */
/* Dashboard Right Panel                                               */
/* ------------------------------------------------------------------ */

export interface DashboardRightPanelProps {
  onFindRoutes: (origin: string, destination: string, mode: string) => void;
  onQuickAction: (actionId: string) => void;
  areaRiskBand: SafetyBand | null;
  areaConfidence: ConfidenceLevel | null;
  statusLoading: boolean;
  routeLoading: boolean;
}

export function DashboardRightPanel({
  onFindRoutes,
  onQuickAction,
  areaRiskBand,
  areaConfidence,
  statusLoading,
  routeLoading,
}: DashboardRightPanelProps) {
  const [activeTab, setActiveTab] = useState<"route" | "share" | "guardian">("route");
  const [origin, setOrigin] = useState("Current Location");
  const [destination, setDestination] = useState("");
  const [mode, setMode] = useState("walking");
  const [preference, setPreference] = useState<SafetyPreference>("safety");

  const handlePlanRoute = useCallback(() => {
    if (!destination.trim()) return;
    onFindRoutes(origin, destination, mode);
  }, [origin, destination, mode, onFindRoutes]);

  return (
    <aside className="dashboard-right-panel" aria-label="Route planning and quick actions">
      {/* Tabs */}
      <div className="dashboard-tabs">
        {[
          { id: "route" as const, icon: RouteIcon, label: "Route" },
          { id: "share" as const, icon: Share2, label: "Share" },
          { id: "guardian" as const, icon: ShieldCheck, label: "Guardian" },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              type="button"
              className={`dashboard-tab ${activeTab === tab.id ? "is-active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon className="size-3.5" aria-hidden />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === "route" && (
          <div className="flex flex-col gap-4">
            {/* From / To inputs */}
            <div className="dashboard-input-group">
              <div>
                <p className="mb-1.5 text-xs font-semibold text-text-muted">From</p>
                <div className="dashboard-input-wrapper">
                  <span className="dashboard-input-icon">
                    <Crosshair className="size-4 text-primary" aria-hidden />
                  </span>
                  <input
                    type="text"
                    value={origin}
                    onChange={(e) => setOrigin(e.target.value)}
                    placeholder="Current Location"
                    aria-label="Origin location"
                  />
                  <button
                    type="button"
                    className="dashboard-input-action"
                    aria-label="Use current location"
                    onClick={() => setOrigin("Current Location")}
                  >
                    <Crosshair className="size-3.5" aria-hidden />
                  </button>
                </div>
              </div>

              <div>
                <p className="mb-1.5 text-xs font-semibold text-text-muted">To</p>
                <div className="dashboard-input-wrapper">
                  <span className="dashboard-input-icon">
                    <MapPin className="size-4 text-emergency" aria-hidden />
                  </span>
                  <input
                    type="text"
                    value={destination}
                    onChange={(e) => setDestination(e.target.value)}
                    placeholder="India Gate, New Delhi"
                    aria-label="Destination"
                  />
                  {destination && (
                    <button
                      type="button"
                      className="dashboard-input-action"
                      onClick={() => setDestination("")}
                      aria-label="Clear destination"
                    >
                      <X className="size-3.5" aria-hidden />
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Transport mode */}
            <TransportModePicker value={mode} onChange={setMode} />

            {/* Safety preference */}
            <div>
              <div className="dashboard-section-header">
                <span className="dashboard-section-title">
                  <Shield className="size-3.5 text-primary" aria-hidden />
                  Safety Preference
                </span>
              </div>
              <div className="grid grid-cols-3 gap-1.5">
                {PREFERENCES.map((p) => {
                  const active = preference === p.id;
                  const Icon = p.icon;
                  return (
                    <button
                      key={p.id}
                      type="button"
                      aria-pressed={active}
                      onClick={() => setPreference(p.id)}
                      className={`flex min-h-[72px] cursor-pointer flex-col items-center gap-1.5 rounded-xl border p-3 text-center transition-colors ${
                        active
                          ? "border-primary/40 bg-primary/8"
                          : "border-border bg-surface hover:border-primary/25"
                      }`}
                    >
                      <span
                        className={`flex size-7 items-center justify-center rounded-lg ${
                          active ? "bg-primary/15 text-primary" : "bg-surface-hover text-text-muted"
                        }`}
                      >
                        <Icon className="size-3.5" aria-hidden />
                      </span>
                      <span className="text-[11px] font-semibold text-foreground">{p.label}</span>
                      <span className="text-[10px] leading-tight text-text-muted">{p.detail}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Plan Route button */}
            <button
              type="button"
              className="plan-route-btn"
              onClick={handlePlanRoute}
              disabled={routeLoading || !destination.trim()}
            >
              <RouteIcon className="size-4" aria-hidden />
              {routeLoading ? "Planning..." : "Plan Route"}
            </button>

            {/* Quick Actions */}
            <div>
              <div className="dashboard-section-header">
                <span className="dashboard-section-title">Quick Actions</span>
                <Link href="/live" className="dashboard-section-link">
                  See All
                </Link>
              </div>
              <QuickActionsGrid onAction={onQuickAction} />
            </div>

            {/* Live Status */}
            <LiveStatusSection
              band={areaRiskBand}
              confidence={areaConfidence}
              loading={statusLoading}
            />

            {/* Encouragement banner */}
            <div className="encouragement-banner">
              <p className="relative text-sm font-bold text-foreground">
                You&apos;re not alone. We&apos;re here for you.
              </p>
              <p className="relative mt-1 text-[11px] text-text-secondary">
                Share your location with trusted contacts in one tap.
              </p>
              <Link
                href="/contacts"
                className="relative mt-2 inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-[11px] font-semibold text-white shadow-md shadow-primary/20 transition-colors hover:bg-primary-hover"
              >
                Enable Now
              </Link>
            </div>
          </div>
        )}

        {activeTab === "share" && (
          <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
            <Share2 className="size-10 text-text-muted" aria-hidden />
            <p className="text-sm font-semibold text-foreground">Share Your Trip</p>
            <p className="text-xs text-text-muted">
              Plan a route first, then share it with your trusted contacts.
            </p>
            <Link
              href="/contacts"
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white shadow-md shadow-primary/20 transition-colors hover:bg-primary-hover"
            >
              Manage Contacts
            </Link>
          </div>
        )}

        {activeTab === "guardian" && (
          <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
            <ShieldCheck className="size-10 text-text-muted" aria-hidden />
            <p className="text-sm font-semibold text-foreground">Guardian Mode</p>
            <p className="text-xs text-text-muted">
              Set up a guardian to track your journey and receive automatic check-in alerts.
            </p>
            <Link
              href="/live#guardian"
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white shadow-md shadow-primary/20 transition-colors hover:bg-primary-hover"
            >
              Set Up Guardian
            </Link>
          </div>
        )}
      </div>
    </aside>
  );
}
