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
    // CSP for sandboxed agent-artefact iframes. The iframe is rendered with
    // `sandbox="allow-scripts"` and no `allow-same-origin`, which gives the
    // document an opaque origin. In that context CSP `'self'` resolves to
    // nothing and a relative `<script src="app.js">` is refused even when
    // the bytes are served correctly. Allowlisting the dev-server origins
    // explicitly unblocks the script load. The sandbox itself remains the
    // security boundary; expanding script-src to a host allowlist does not
    // let the iframe reach parent state. Add the production hosted origin
    // here when the deployment URL is known.
    const DEV_ORIGINS =
      "http://127.0.0.1:3000 http://localhost:3000 http://127.0.0.1:8000 http://localhost:8000";
    const CSP =
      `default-src 'none'; script-src 'self' 'unsafe-inline' ${DEV_ORIGINS}; ` +
      `style-src 'self' 'unsafe-inline' ${DEV_ORIGINS}; ` +
      `img-src 'self' data: ${DEV_ORIGINS}; ` +
      `font-src 'self' data: ${DEV_ORIGINS}`;
    return [
      {
        source: "/api/mocks/projects/:pid/static/:path*",
        headers: [
          { key: "Content-Security-Policy", value: CSP },
          { key: "Cache-Control", value: "private, max-age=60" },
        ],
      },
      {
        source: "/api/sim/:id/projects/:pid/static/:path*",
        headers: [
          { key: "Content-Security-Policy", value: CSP },
          { key: "Cache-Control", value: "private, max-age=60" },
        ],
      },
    ];
  },
};

export default config;
