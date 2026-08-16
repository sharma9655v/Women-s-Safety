"use client";

import { Phone } from "lucide-react";
import { useSos } from "@/app/components/shell/AppShell";
import { useI18n } from "@/lib/i18n";

export function EmergencyCard() {
  const openSos = useSos();
  const { t } = useI18n();

  return (
    <button
      type="button"
      onClick={openSos}
      className="group flex min-h-12 w-full cursor-pointer items-center gap-3 rounded-xl bg-emergency/10 px-3 py-2.5 text-left transition-all duration-200 hover:bg-emergency/18"
    >
      <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-emergency text-white shadow-md animate-ring-pulse">
        <Phone className="size-4" aria-hidden />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-bold text-emergency">{t("emergency.sos")}</p>
        <p className="text-[10px] text-text-muted">{t("emergency.tapForHelp")}</p>
      </div>
    </button>
  );
}
