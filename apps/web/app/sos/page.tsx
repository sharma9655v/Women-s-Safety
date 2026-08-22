"use client";
import { SOSButton } from "@/components/sos/SOSButton";
import { GuardianPanel } from "@/components/sos/GuardianPanel";
import { JourneyCheckin } from "@/components/sos/JourneyCheckin";
import { FakeCallCard } from "@/components/sos/FakeCallCard";
import { VoiceCard } from "@/components/sos/VoiceCard";
import { Card } from "@/components/ui/Card";
import { Tabs } from "@/components/ui/Tabs";
import { Shield, AlertTriangle, Flag, Phone, Mic, Loader2 } from "lucide-react";

export default function SosPage() {
  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      {/* Emergency header */}
      <div className="p-4 sm:p-6 border-b border-line bg-emergency/10">
        <div className="mx-auto max-w-4xl">
          <div className="flex items-center gap-3 mb-2">
            <div className="size-12 rounded-xl bg-emergency/20 flex items-center justify-center"><AlertTriangle size={24} className="text-emergency" /></div>
            <div>
              <h1 className="font-display text-2xl font-bold text-emergency">Emergency Hub</h1>
              <p className="text-sm text-text-mid">All safety tools in one place. Long-press SOS to alert contacts immediately.</p>
            </div>
          </div>
          <div className="glass p-3 rounded-xl text-center">
            <p className="text-sm text-text-mid">Your location is shared only when you activate a feature. No background tracking.</p>
          </div>
        </div>
      </div>

      {/* Main SOS button - always visible */}
      <div className="flex-1 flex items-center justify-center px-4">
        <SOSButton />
      </div>

      {/* Feature tabs below */}
      <div className="border-t border-line bg-surface/50">
        <Tabs defaultValue="guardian" items={[
          { value: "guardian", label: "Guardian" },
          { value: "journey", label: "Journey" },
          { value: "fake-call", label: "Fake Call" },
          { value: "voice", label: "Voice" },
        ]}>
          {(tab) => (
            <div className="p-4 sm:p-6 max-w-4xl mx-auto w-full">
              {tab === "guardian" && <GuardianPanel />}
              {tab === "journey" && <JourneyCheckin />}
              {tab === "fake-call" && <FakeCallCard />}
              {tab === "voice" && <VoiceCard />}
            </div>
          )}
        </Tabs>
      </div>

      {/* Disclaimer */}
      <footer className="p-4 border-t border-line text-center text-xs text-text-low">
        <p>Emergency features require network connectivity. Always call local emergency services (112/100) for immediate danger.</p>
      </footer>
    </div>
  );
}