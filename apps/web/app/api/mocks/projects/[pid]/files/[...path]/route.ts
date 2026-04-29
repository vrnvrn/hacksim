import { promises as fs } from "node:fs";
import path from "node:path";

// GET /api/mocks/projects/:pid/files/<path>. Returns the raw bytes of a file
// inside a mock project's static tree. Used by the Code tab to fetch source
// on demand. Stays inside the project's static directory; rejects path
// traversal.
export async function GET(
  _req: Request,
  ctx: { params: Promise<{ pid: string; path: string[] }> },
) {
  const { pid, path: parts } = await ctx.params;
  const joined = (parts ?? []).join("/");
  if (!joined || joined.includes("..") || joined.startsWith("/")) {
    return new Response("invalid path", { status: 400 });
  }
  const root = path.join(
    process.cwd(),
    "lib",
    "mocks",
    "projects",
    pid,
    "static",
  );
  const target = path.join(root, joined);
  if (!target.startsWith(root)) {
    return new Response("invalid path", { status: 400 });
  }
  try {
    const buf = await fs.readFile(target);
    return new Response(buf, {
      status: 200,
      headers: { "Content-Type": guessMime(joined) },
    });
  } catch {
    return new Response("not found", { status: 404 });
  }
}

function guessMime(p: string): string {
  const ext = p.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "html":
      return "text/html; charset=utf-8";
    case "css":
      return "text/css; charset=utf-8";
    case "js":
    case "mjs":
      return "text/javascript; charset=utf-8";
    case "json":
      return "application/json; charset=utf-8";
    case "svg":
      return "image/svg+xml";
    case "png":
      return "image/png";
    case "jpg":
    case "jpeg":
      return "image/jpeg";
    default:
      return "text/plain; charset=utf-8";
  }
}
