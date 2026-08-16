"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type Lang = "en" | "hi";

interface Dict {
  appName: string;
  tagline: string;
  nav: Record<string, string>;
  header: Record<string, string>;
  common: Record<string, string>;
  emergency: Record<string, string>;
}

const EN: Dict = {
  appName: "Map for Women",
  tagline: "Safer Routes · Stronger Cities",
  nav: {
    map: "Map",
    insights: "Insights",
    alerts: "Alerts",
    report: "Report",
    guardian: "Guardian",
    contacts: "Trusted Contacts",
    community: "Community",
    civic: "Civic Ops",
    sources: "Data Sources",
    admin: "Review Queue",
    profile: "Profile",
    settings: "Settings",
    privacy: "Privacy Center",
    emergency: "Emergency",
  },
  header: {
    search: "Search for a place, area or address...",
    region: "Delhi, India",
    theme: "Theme",
    language: "Language",
    notifications: "Notifications",
  },
  common: {
    back: "Back",
    close: "Close",
    cancel: "Cancel",
    confirm: "Confirm",
    save: "Save",
    loading: "Loading…",
    unavailable: "Unavailable right now",
  },
  emergency: {
    sos: "SOS",
    tapForHelp: "Tap for help options",
    callHelpline: "Call a helpline",
    shareLocation: "Share live location",
    startGuardian: "Start guardian mode",
  },
};

const HI: Dict = {
  appName: "महिलाओं के लिए नक्शा",
  tagline: "सुरक्षित मार्ग · मज़बूत शहर",
  nav: {
    map: "नक्शा",
    insights: "अंतर्दृष्टि",
    alerts: "अलर्ट",
    report: "रिपोर्ट",
    guardian: "गार्डियन",
    contacts: "विश्वसनीय संपर्क",
    community: "समुदाय",
    civic: "नागरिक संचालन",
    sources: "डेटा स्रोत",
    admin: "समीक्षा कतार",
    profile: "प्रोफ़ाइल",
    settings: "सेटिंग्स",
    privacy: "गोपनीयता केंद्र",
    emergency: "आपातकाल",
  },
  header: {
    search: "कोई स्थान, क्षेत्र या पता खोजें...",
    region: "दिल्ली, भारत",
    theme: "थीम",
    language: "भाषा",
    notifications: "सूचनाएँ",
  },
  common: {
    back: "वापस",
    close: "बंद करें",
    cancel: "रद्द करें",
    confirm: "पुष्टि करें",
    save: "सहेजें",
    loading: "लोड हो रहा है…",
    unavailable: "अभी अनुपलब्ध",
  },
  emergency: {
    sos: "एसओएस",
    tapForHelp: "मदद विकल्पों के लिए टैप करें",
    callHelpline: "हेल्पलाइन पर कॉल करें",
    shareLocation: "लाइव स्थान साझा करें",
    startGuardian: "गार्डियन मोड शुरू करें",
  },
};

const DICTS: Record<Lang, typeof EN> = { en: EN, hi: HI };
const STORAGE_KEY = "mf:lang";

export type TKey = "appName" | "tagline" | `${"nav" | "header" | "common" | "emergency"}.${string}`;

interface I18nValue {
  lang: Lang;
  t: (key: TKey) => string;
  setLang: (lang: Lang) => void;
}

const I18nContext = createContext<I18nValue>({
  lang: "en",
  t: (key) => key,
  setLang: () => {},
});

export function useI18n(): I18nValue {
  return useContext(I18nContext);
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored === "en" || stored === "hi") setLangState(stored);
    } catch {
      // storage unavailable — keep default
    }
  }, []);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // storage unavailable — session-only
    }
    document.documentElement.lang = next;
  }, []);

  const t = useCallback(
    (key: TKey): string => {
      const dict = DICTS[lang];
      const parts = key.split(".");
      let value: unknown = dict;
      for (const part of parts) {
        value = (value as Record<string, unknown> | undefined)?.[part];
      }
      return typeof value === "string" ? value : key;
    },
    [lang],
  );

  const value = useMemo(() => ({ lang, t, setLang }), [lang, t, setLang]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}
