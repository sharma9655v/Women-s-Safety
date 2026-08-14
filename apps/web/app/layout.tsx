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

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} ${spaceGrotesk.variable} ${geistMono.variable}`}>
      <body>
        <ThemeInitScript />
        <ThemeProvider>
          <AppShell>{children}</AppShell>
        </ThemeProvider>
      </body>
    </html>
  );
}
