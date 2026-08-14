"use client";

import { createContext, type ReactNode, useCallback, useContext, useState } from "react";
import { SOSConfirmation } from "@/app/components/emergency/SOSConfirmation";
import { PageTransition } from "@/app/components/motion/PageTransition";
import { MobileNav } from "./MobileNav";
import { Sidebar } from "./Sidebar";
import { TopHeader } from "./TopHeader";

const SosContext = createContext<() => void>(() => {});

export function useSos(): () => void {
  return useContext(SosContext);
}

function AuroraBackdrop() {
  return <div aria-hidden className="aurora-backdrop" />;
}

export function AppShell({ children }: { children: ReactNode }) {
  const [sosOpen, setSosOpen] = useState(false);

  return (
    <SosContext.Provider value={useCallback(() => setSosOpen(true), [])}>
      <AuroraBackdrop />
      <div className="relative z-10 flex h-dvh overflow-hidden bg-transparent text-foreground">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopHeader />
          <main className="min-h-0 flex-1">
            <PageTransition>{children}</PageTransition>
          </main>
        </div>
        <MobileNav />
      </div>
      <SOSConfirmation open={sosOpen} onClose={() => setSosOpen(false)} />
    </SosContext.Provider>
  );
}
