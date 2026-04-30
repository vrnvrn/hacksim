/**
 * HostedModeBanner. Renders only when this build is the hosted preview on
 * Vercel (NEXT_PUBLIC_HOSTED_PREVIEW=true) and the public-facing build is
 * running against fixtures (NEXT_PUBLIC_USE_MOCKS=true). Tells judges
 * exactly what they are looking at so a fixture cannot be mistaken for a
 * live AXL mesh.
 *
 * Both env vars are read at build time. The banner compiles out entirely
 * for local pnpm dev (where neither var is set) and for Mode V2 deploys
 * with NEXT_PUBLIC_USE_MOCKS=false.
 */
import Link from "next/link";

const HOSTED = process.env.NEXT_PUBLIC_HOSTED_PREVIEW === "true";
const MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";

export function HostedModeBanner() {
  if (!HOSTED || !MOCKS) return null;
  return (
    <aside
      role="note"
      aria-label="Hosted preview notice"
      className="max-w-7xl mx-auto px-6 lg:px-8 pt-4"
    >
      <div className="rounded-2xl border border-border bg-canvas/70 px-4 py-3 text-sm text-body flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="text-xs font-mono uppercase tracking-[0.18em] text-accent shrink-0">
          [ hosted preview ]
        </span>
        <span className="leading-relaxed">
          You are looking at the Vercel build running against fixtures, not a
          live AXL mesh. The hero and example tiles still spin up a sim, but
          the snapshot, the run log, and the showcase artefacts replay
          recorded ndjson and three demo projects. To watch real AXL nodes
          peer through Yggdrasil, run{" "}
          <code className="rounded bg-surface px-1.5 py-0.5 font-mono text-[0.85em] text-ink">
            make demo
          </code>{" "}
          from a clone.
        </span>
        <Link
          href="https://github.com/vrnvrn/hacksim"
          target="_blank"
          rel="noreferrer"
          className="text-xs font-medium text-accent hover:underline shrink-0"
        >
          Repo &rarr;
        </Link>
      </div>
    </aside>
  );
}
