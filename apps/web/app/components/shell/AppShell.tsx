"use client";

import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { SOSConfirmation } from "@/app/components/emergency/SOSConfirmation";
import { PageTransition } from "@/app/components/motion/PageTransition";
import { fetchActiveEmergency, fetchDiscreetMode } from "@/lib/api";
import { I18nProvider } from "@/lib/i18n";
import type { EmergencySession } from "@/lib/types";
import { MobileNav } from "./MobileNav";
import { Sidebar } from "./Sidebar";
import { TopHeader } from "./TopHeader";

const SosContext = createContext<() => void>(() => {});

export function useSos(): () => void {
  return useContext(SosContext);
}

export interface DiscreetModeState {
  enabled: boolean;
  /** Neutral name the app masquerades as while discreet mode is on. */
  label: string;
  /** Neutral icon key used while discreet mode is on. */
  icon: string;
  loading: boolean;
}

const DiscreetContext = createContext<DiscreetModeState>({
  enabled: false,
  label: "Weather",
  icon: "cloud",
  loading: true,
});

export function useDiscreetMode(): DiscreetModeState {
  return useContext(DiscreetContext);
}

function AuroraBackdrop() {
  return <div aria-hidden className="aurora-backdrop" />;
}

export function AppShell({ children }: { children: ReactNode }) {
  const [sosOpen, setSosOpen] = useState(false);
  const [restoredSession, setRestoredSession] = useState<EmergencySession | null>(null);
  const [discreet, setDiscreet] = useState<DiscreetModeState>({
    enabled: false,
    label: "Weather",
    icon: "cloud",
    loading: true,
  });

  useEffect(() => {
    let cancelled = false;
    fetchDiscreetMode()
      .then((d) => {
        if (cancelled) return;
        setDiscreet({
          enabled: d.enabled,
          label: d.neutral_app_label || "Weather",
          icon: d.neutral_app_icon || "cloud",
          loading: false,
        });
      })
      .catch(() => {
        if (!cancelled) setDiscreet((prev) => ({ ...prev, loading: false }));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // While discreet mode is on, the browser tab shows the neutral label too.
  useEffect(() => {
    const original = document.title;
    if (discreet.enabled && !discreet.loading) {
      document.title = discreet.label;
    }
    return () => {
      document.title = original;
    };
  }, [discreet.enabled, discreet.loading, discreet.label]);

  // Restore an in-progress emergency after a page reload.
  useEffect(() => {
    let cancelled = false;
    fetchActiveEmergency()
      .then((s) => {
        if (cancelled || !s || s.status !== "ACTIVE") return;
        setRestoredSession(s);
        setSosOpen(true);
      })
      .catch(() => {
        // backend unreachable — the modal still offers helplines
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const openSos = useCallback(() => {
    setRestoredSession(null);
    setSosOpen(true);
  }, []);

  return (
    <I18nProvider>
      <SosContext.Provider value={openSos}>
        <DiscreetContext.Provider value={discreet}>
          <AuroraBackdrop />
          <a href="#main-content" className="skip-link">
            Skip to content
          </a>
          <div className="app-shell relative z-10 flex h-dvh overflow-hidden bg-transparent text-foreground">
            <Sidebar />
            <div className="flex min-w-0 flex-1 flex-col">
              <TopHeader />
              <main id="main-content" className="app-main min-h-0 flex-1">
                <PageTransition>{children}</PageTransition>
              </main>
            </div>
            <MobileNav />
          </div>
          <SOSConfirmation
            open={sosOpen}
            onClose={() => setSosOpen(false)}
            restoredSession={restoredSession}
          />
        </DiscreetContext.Provider>
      </SosContext.Provider>
    </I18nProvider>
  );
}
