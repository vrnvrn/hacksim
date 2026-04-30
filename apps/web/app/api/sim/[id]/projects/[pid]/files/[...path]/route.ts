// GET /api/sim/:id/projects/:pid/files/<relpath>. Proxies raw file bytes from the
// orchestrator for the Code tab. The list-only route at .../files/route.ts handles
// JSON metadata; this catch-all forwards each file's body. Without it,
// getProjectFileContents() hits Next with no matching handler, the modal swallows the
// error as empty content, and SourceView shows "1 lines" on a blank panel.

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ id: string; pid: string; path: string[] }> },
) {
  const { id, pid, path } = await ctx.params;
  const joined = (path ?? []).join("/");
  if (!joined || joined.includes("..") || joined.startsWith("/")) {
    return new Response("invalid path", { status: 400 });
  }
  const urlPath = joined
    .split("/")
    .map((seg) => encodeURIComponent(seg))
    .join("/");
  const base = process.env.ORCHESTRATOR_BASE_URL ?? "http://127.0.0.1:8000";
  try {
    const upstream = await fetch(
      `${base}/api/sim/${encodeURIComponent(id)}/projects/${encodeURIComponent(pid)}/files/${urlPath}`,
      { cache: "no-store" },
    );
    const buf = await upstream.arrayBuffer();
    const headers = new Headers(upstream.headers);
    return new Response(buf, { status: upstream.status, headers });
  } catch {
    return new Response("orchestrator unreachable", { status: 502 });
  }
}
