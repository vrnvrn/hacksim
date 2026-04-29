import { NextResponse } from "next/server";

// POST /api/sim. In mock mode we return a fixed sim id so the user lands on
// the live page wired to the snapshot fixture. In real mode we proxy to the
// FastAPI orchestrator at ORCHESTRATOR_BASE_URL.
const MOCK_SIM_ID = "sim_2026-04-28_a1b2c3";

export async function POST(req: Request) {
  const useMocks = process.env.NEXT_PUBLIC_USE_MOCKS === "true";
  const body = await req.json().catch(() => ({}));

  if (useMocks) {
    return NextResponse.json(
      {
        id: MOCK_SIM_ID,
        stream_url: `/api/mocks/stream?id=${MOCK_SIM_ID}`,
      },
      { status: 201 },
    );
  }

  const base = process.env.ORCHESTRATOR_BASE_URL ?? "http://127.0.0.1:8000";
  try {
    const upstream = await fetch(`${base}/api/sim`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
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
