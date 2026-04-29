import { NextResponse } from "next/server";

// GET /api/sim/:id/snapshot. Thin proxy. In mock mode this route is not
// called; the page hits /api/mocks/snapshot directly. We keep the shape
// identical so flipping NEXT_PUBLIC_USE_MOCKS=false swaps the source with no
// other code change.
export async function GET(
  _req: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  const { id } = await ctx.params;
  const base = process.env.ORCHESTRATOR_BASE_URL ?? "http://127.0.0.1:8000";
  try {
    const upstream = await fetch(`${base}/api/sim/${encodeURIComponent(id)}/snapshot`, {
      cache: "no-store",
    });
    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return NextResponse.json(
      { error: "orchestrator unreachable" },
      { status: 502 },
    );
  }
}
