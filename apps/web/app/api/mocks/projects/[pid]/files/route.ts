import { NextResponse } from "next/server";
import { promises as fs } from "node:fs";
import path from "node:path";

// GET /api/mocks/projects/:pid/files. Returns the files.json fixture for the
// given mock project. Mirrors the real backend's GET
// /api/sim/:id/projects/:pid/files shape.
export async function GET(
  _req: Request,
  ctx: { params: Promise<{ pid: string }> },
) {
  const { pid } = await ctx.params;
  const filesPath = path.join(
    process.cwd(),
    "lib",
    "mocks",
    "projects",
    pid,
    "files.json",
  );
  try {
    const raw = await fs.readFile(filesPath, "utf8");
    return new NextResponse(raw, {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return NextResponse.json(
      { error: `unknown mock project ${pid}` },
      { status: 404 },
    );
  }
}
