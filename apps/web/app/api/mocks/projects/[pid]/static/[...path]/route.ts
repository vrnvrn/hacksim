import { promises as fs } from "node:fs";
import path from "node:path";

// Match the live route CSP. The iframe sandbox makes the document origin
// opaque so CSP `'self'` cannot resolve; an explicit dev-origin allowlist
// keeps relative scripts loading. See the matching comment in
// app/api/sim/[id]/projects/[pid]/static/[...path]/route.ts.
const DEV_ORIGINS =
  "http://127.0.0.1:3000 http://localhost:3000 http://127.0.0.1:8000 http://localhost:8000";
const CSP =
  `default-src 'none'; script-src 'self' 'unsafe-inline' ${DEV_ORIGINS}; ` +
  `style-src 'self' 'unsafe-inline' ${DEV_ORIGINS}; ` +
  `img-src 'self' data: ${DEV_ORIGINS}; ` +
  `font-src 'self' data: ${DEV_ORIGINS}`;

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
