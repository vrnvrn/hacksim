// GET /api/sim/:id/projects/:pid/static/<path>. Proxies the static artefact
// from the orchestrator with the strict CSP attached in next.config.ts. In
// production nginx (or FastAPI directly) serves these files; this dev route
// exists so `next dev` keeps working with the same URL shape.

// Explicitly allow the dev-server origins as script and style sources so
// sandboxed iframes can load relative scripts. The iframe is rendered with
// `sandbox="allow-scripts"` and no `allow-same-origin`, which makes the
// document's effective origin opaque. In that context CSP `'self'` matches
// nothing, so `<script src="app.js">` was blocked even though the bytes
// were served correctly. The sandbox is still the security boundary;
// expanding script-src to a host allowlist does not weaken it.
const DEV_ORIGINS =
  "http://127.0.0.1:3000 http://localhost:3000 http://127.0.0.1:8000 http://localhost:8000";

const CSP =
  `default-src 'none'; script-src 'self' 'unsafe-inline' ${DEV_ORIGINS}; ` +
  `style-src 'self' 'unsafe-inline' ${DEV_ORIGINS}; ` +
  `img-src 'self' data: ${DEV_ORIGINS}; ` +
  `font-src 'self' data: ${DEV_ORIGINS}`;

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ id: string; pid: string; path: string[] }> },
) {
  const { id, pid, path } = await ctx.params;
  const joined = (path ?? []).join("/");
  const base = process.env.ORCHESTRATOR_BASE_URL ?? "http://127.0.0.1:8000";
  try {
    const upstream = await fetch(
      `${base}/api/sim/${encodeURIComponent(id)}/projects/${encodeURIComponent(pid)}/static/${joined}`,
      { cache: "no-store" },
    );
    const buf = await upstream.arrayBuffer();
    const headers = new Headers(upstream.headers);
    headers.set("Content-Security-Policy", CSP);
    headers.set("Cache-Control", "private, max-age=60");
    return new Response(buf, { status: upstream.status, headers });
  } catch {
    return new Response("orchestrator unreachable", { status: 502 });
  }
}
