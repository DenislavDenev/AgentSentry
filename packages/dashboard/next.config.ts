import type { NextConfig } from "next"

const WATCHTOWER = process.env.WATCHTOWER_URL ?? "http://localhost:8000"

const nextConfig: NextConfig = {
  output: "standalone",
  // Proxy /api/* → Watchtower so browser-side fetches work regardless of
  // where the dashboard is accessed from (avoids hardcoding the LAN IP).
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${WATCHTOWER}/:path*`,
      },
    ]
  },
}

export default nextConfig
