import type { Metadata } from "next";
import { Geist_Mono, Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { AppShell } from "./components/shell/AppShell";
import { ThemeProvider } from "./components/theme/ThemeProvider";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Map for Women — Safety-Aware Navigation",
  description:
    "Safety-aware navigation platform. Estimates route risk using time-aware evidence. Never guarantees safety.",
};

/** Apply the persisted/resolved theme before first paint to avoid a flash. */
function ThemeInitScript() {
  return (
    <script
      // biome-ignore lint/security/noDangerouslySetInnerHtml: static no-FOUC theme bootstrap; no user input
      dangerouslySetInnerHTML={{
        __html: `(function(){try{var t=localStorage.getItem('mf:theme');var d=t==='light'||t==='dark'?t:(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.dataset.theme=d;}catch(e){document.documentElement.dataset.theme='dark';}})();`,
      }}
    />
  );
}

/** Register the PWA service worker. Honest cache policy lives in /sw.js. */
function ServiceWorkerScript() {
  return (
    <script
      // biome-ignore lint/security/noDangerouslySetInnerHtml: static bootstrap; no user input
      dangerouslySetInnerHTML={{
        __html: `(function(){if(!('serviceWorker' in navigator))return;var ok=location.protocol==='https:'||location.hostname==='localhost'||location.hostname==='127.0.0.1';if(!ok)return;addEventListener('load',function(){navigator.serviceWorker.register('/sw.js').catch(function(){})});})();`,
      }}
    />
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // suppressHydrationWarning: the no-FOUC ThemeInitScript sets data-theme
  // before hydration; the attribute is styling state, not markup.
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${spaceGrotesk.variable} ${geistMono.variable}`}
    >
      <body>
        <ThemeInitScript />
        <ServiceWorkerScript />
        <ThemeProvider>
          <AppShell>{children}</AppShell>
        </ThemeProvider>
      </body>
    </html>
  );
}
