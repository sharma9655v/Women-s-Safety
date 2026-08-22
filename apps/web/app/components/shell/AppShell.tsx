"use client";
import { ReactNode, useState } from "react";
import { TopHeader } from "./TopHeader";
import { Sidebar } from "./Sidebar";
import { MobileNav } from "./MobileNav";

export function AppShell({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  return (
    <div className="min-h-screen flex flex-col">
      <TopHeader />
      <div className="flex-1 flex">
        <MobileNav />
        <aside className="hidden lg:block">
          <Sidebar onClose={() => setSidebarOpen(false)} />
        </aside>
        <main className="flex-1 min-w-0">{children}</main>
      </div>
    </div>
  );
}