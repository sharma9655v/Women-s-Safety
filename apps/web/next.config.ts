import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  typescript: {
    ignoreBuildErrors: true,
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          // Never let other origins frame the app (clickjacking).
          { key: "X-Frame-Options", value: "DENY" },
          // No MIME sniffing.
          { key: "X-Content-Type-Options", value: "nosniff" },
          // Referrer stripped down to the origin.
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          // No cross-origin resource fetching capabilities beyond what the
          // app itself needs.
          { key: "Permissions-Policy", value: "geolocation=(self), camera=(), microphone=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
