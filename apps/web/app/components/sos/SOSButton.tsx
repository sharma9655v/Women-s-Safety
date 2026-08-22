"use client";
import { useRef, useState, useCallback, useEffect } from "react";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";
import { Shield, AlertCircle, Loader2, Check, X } from "lucide-react";

const LONG_PRESS_MS = 1500;

export function SOSButton() {
  const router = useRouter();
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<"idle" | "triggered" | "error">("idle");
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const watchId = useRef(0);
  const pos = useRef<GeolocationPosition | null>(null);

  useEffect(() => {
    if (!navigator.geolocation) return;
    const handlePosition = (p: GeolocationPosition): void => { pos.current = p; };
    watchId.current = navigator.geolocation.watchPosition(handlePosition, () => {}, { enableHighAccuracy: true, maximumAge: 10000, timeout: 5000 });
    return () => navigator.geolocation.clearWatch(watchId.current);
  }, []);

  const fire = useCallback(async () => {
    setStatus("triggered");
    const c = pos.current?.coords;
    try {
      const session = await api.emergency.start({ kind: "sos", lat: c?.latitude ?? null, lon: c?.longitude ?? null, source_client_id: undefined });
      router.push(`/sos/${session.session_id}`);
    } catch {
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
    }
  }, [router]);

  const start = () => {
    const t0 = performance.now();
    timer.current = setInterval(() => setProgress(Math.min((performance.now() - t0) / LONG_PRESS_MS, 1)), 33);
  };
  const cancel = () => { if (timer.current) clearInterval(timer.current); setProgress(0); };

  return (
    <button aria-label="Hold to send SOS" onPointerDown={start} onPointerUp={progress >= 1 ? fire : cancel} onPointerLeave={cancel} onPointerCancel={cancel} className={`relative grid size-44 sm:size-52 place-items-center rounded-full border-4 border-emergency/30 shadow-emergency-glow transition-all select-none touch-none ${status === "error" ? "animate-shake border-danger" : ""}`}>
      <svg className="absolute inset-0 -rotate-90"><circle r="70" cx="112" cy="112" fill="none" stroke="currentColor" strokeWidth="8" strokeDasharray={440} strokeDashoffset={440 * (1 - progress)} strokeLinecap="round" className="text-emergency" /></svg>
      <div className="relative z-10 flex flex-col items-center gap-1">
        {status === "triggered" ? <svg width={28} height={28} className="animate-spin text-emergency" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" strokeOpacity="0.25"/><path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round"/></svg> : status === "error" ? <X width={28} height={28} className="text-danger" /> : <Shield width={progress >= 1 ? 36 : 28} height={progress >= 1 ? 36 : 28} className="text-emergency transition-transform" />}
        <span className="font-display text-sm sm:text-base tracking-widest text-emergency font-bold">{progress >= 1 ? "SENT" : "HOLD"}</span>
      </div>
    </button>
  );
}