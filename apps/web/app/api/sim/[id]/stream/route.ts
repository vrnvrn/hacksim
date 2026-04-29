// GET /api/sim/:id/stream. SSE proxy. We let fetch surface the upstream
// stream as a ReadableStream so envelopes pass through line by line.
export async function GET(
  _req: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  const { id } = await ctx.params;
  const base = process.env.ORCHESTRATOR_BASE_URL ?? "http://127.0.0.1:8000";
  try {
    const upstream = await fetch(
      `${base}/api/sim/${encodeURIComponent(id)}/stream`,
      { cache: "no-store" },
    );
    if (!upstream.body) {
      return new Response("upstream had no body", { status: 502 });
    }
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      },
    });
  } catch {
    return new Response("orchestrator unreachable", { status: 502 });
  }
}
