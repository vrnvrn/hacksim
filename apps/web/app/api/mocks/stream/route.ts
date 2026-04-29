import { promises as fs } from "node:fs";
import path from "node:path";

// GET /api/mocks/stream. Replays the ndjson fixture as an SSE stream at 1.5x
// real time, preserving the gaps between events so the live page feels
// realistic. Each line of the ndjson is one envelope; the route writes
// `data: <line>\n\n` to the stream.
export async function GET(req: Request) {
  const fixturePath = path.join(
    process.cwd(),
    "lib",
    "mocks",
    "stream.ndjson",
  );
  let raw: string;
  try {
    raw = await fs.readFile(fixturePath, "utf8");
  } catch {
    return new Response("mock stream missing", { status: 500 });
  }

  const lines = raw
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);

  const encoder = new TextEncoder();
  const url = new URL(req.url);
  const slow = url.searchParams.get("slow") === "1";
  const speed = slow ? 1.0 : 1.5;

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      let cursor: number | null = null;
      // Emit a hello so the client onopen fires promptly.
      controller.enqueue(encoder.encode(`: ready\n\n`));
      for (const line of lines) {
        let env: { ts?: string };
        try {
          env = JSON.parse(line);
        } catch {
          continue;
        }
        if (env.ts && cursor !== null) {
          const next = Date.parse(env.ts);
          const wait = Math.max(0, (next - cursor) / speed);
          // Cap the inter-event gap at 4s so the demo does not stall on a
          // rare big gap in the fixture.
          await new Promise((resolve) =>
            setTimeout(resolve, Math.min(wait, 4000)),
          );
        }
        controller.enqueue(encoder.encode(`data: ${line}\n\n`));
        if (env.ts) cursor = Date.parse(env.ts);
      }
      controller.enqueue(encoder.encode(`event: done\ndata: {}\n\n`));
      controller.close();
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
