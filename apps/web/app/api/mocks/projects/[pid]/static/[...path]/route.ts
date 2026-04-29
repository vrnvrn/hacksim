import { promises as fs } from "node:fs";
import path from "node:path";

const CSP =
  "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:";

// GET /api/mocks/projects/:pid/static/<path>. Serves the iframe contents
// with the same strict CSP the real orchestrator emits. Default to
// index.html when no path is given.
export async function GET(
  _req: Request,
  ctx: { params: Promise<{ pid: string; path: string[] }> },
) {
  const { pid, path: parts } = await ctx.params;
  const joined =
    parts && parts.length > 0 ? parts.join("/") : "index.html";
  if (joined.includes("..") || joined.startsWith("/")) {
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
      headers: {
        "Content-Type": guessMime(joined),
        "Content-Security-Policy": CSP,
        "Cache-Control": "private, max-age=60",
      },
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
