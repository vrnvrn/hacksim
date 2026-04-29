import type { NextConfig } from "next";
import path from "node:path";

const config: NextConfig = {
  reactStrictMode: true,
  // Pin the file-tracing root to this app so Next stops complaining about
  // additional lockfiles in the parent monorepo.
  outputFileTracingRoot: path.resolve(__dirname),
  // The mock-mode default is set via .env.local. The orchestrator serves the
  // real API and static artefacts on its own port; in dev we proxy via the
  // routes under app/api/sim/. In production, nginx (or FastAPI) serves them.
  typedRoutes: false,
  async headers() {
    // The static artefact route inherits the orchestrator's CSP at run time.
    // For the dev mock route we still set a defensive CSP so iframes behave
    // the same way against mocks and real backend.
    return [
      {
        source: "/api/mocks/projects/:pid/static/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value:
              "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:",
          },
          { key: "Cache-Control", value: "private, max-age=60" },
        ],
      },
      {
        source: "/api/sim/:id/projects/:pid/static/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value:
              "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:",
          },
          { key: "Cache-Control", value: "private, max-age=60" },
        ],
      },
    ];
  },
};

export default config;
