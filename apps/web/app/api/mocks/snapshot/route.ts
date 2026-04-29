import { NextResponse } from "next/server";
import { promises as fs } from "node:fs";
import path from "node:path";

// GET /api/mocks/snapshot. Reads the static fixture at request time so we
// can hot-edit the snapshot in dev without restarting the server. Returns
// the same shape as the real /api/sim/:id/snapshot.
export async function GET(req: Request) {
  const url = new URL(req.url);
  const id = url.searchParams.get("id") ?? "sim_2026-04-28_a1b2c3";
  const fixturePath = path.join(
    process.cwd(),
    "lib",
    "mocks",
    "snapshot.json",
  );
  try {
    const raw = await fs.readFile(fixturePath, "utf8");
    const json = JSON.parse(raw) as Record<string, unknown>;
    json.id = id;
    return NextResponse.json(json);
  } catch (e) {
    return NextResponse.json(
      { error: `mock snapshot missing: ${(e as Error).message}` },
      { status: 500 },
    );
  }
}
