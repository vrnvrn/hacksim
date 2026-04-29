// GET /api/sim/:id/projects/:pid/static/<path>. Proxies the static artefact
// from the orchestrator with the strict CSP attached in next.config.ts. In
// production nginx (or FastAPI directly) serves these files; this dev route
// exists so `next dev` keeps working with the same URL shape.

const CSP =
  "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:";

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
