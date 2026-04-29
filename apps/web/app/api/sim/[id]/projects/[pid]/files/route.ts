import { NextResponse } from "next/server";

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ id: string; pid: string }> },
) {
  const { id, pid } = await ctx.params;
  const base = process.env.ORCHESTRATOR_BASE_URL ?? "http://127.0.0.1:8000";
  try {
    const upstream = await fetch(
      `${base}/api/sim/${encodeURIComponent(id)}/projects/${encodeURIComponent(pid)}/files`,
      { cache: "no-store" },
    );
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
