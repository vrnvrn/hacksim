import { NextResponse } from "next/server";

// POST /api/sim/reset. Stops every controller in the FastAPI orchestrator
// and frees the loopback bootstrap port (127.0.0.1:9100). Idempotent;
// safe to call from any state. The Restart button on /sim/[id] hits this.

export async function POST() {
  const useMocks = process.env.NEXT_PUBLIC_USE_MOCKS === "true";
  if (useMocks) {
    return new NextResponse(null, { status: 204 });
  }

  const base = process.env.ORCHESTRATOR_BASE_URL ?? "http://127.0.0.1:8000";
  try {
    const upstream = await fetch(`${base}/api/sim/reset`, { method: "POST" });
    return new NextResponse(null, { status: upstream.status });
  } catch {
    return NextResponse.json(
      { error: "orchestrator unreachable" },
      { status: 502 },
    );
  }
}
