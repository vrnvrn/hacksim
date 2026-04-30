/**
 * HostedModeBanner. Renders only when this build is the hosted preview on
 * Vercel (NEXT_PUBLIC_HOSTED_PREVIEW=true) and the public-facing build is
 * running against fixtures (NEXT_PUBLIC_USE_MOCKS=true). Tells visitors
 * that the page is a recording, not a live AXL mesh, and points them at
 * the canonical demo path: clone, build, run.
 *
 * Both env vars are read at build time. The banner compiles out entirely
 * for local pnpm dev (where neither var is set) and for Mode V2 deploys
 * with NEXT_PUBLIC_USE_MOCKS=false.
 *
 * Mounted in apps/web/app/layout.tsx so every route inherits the notice;
 * the per-page Nav renders below it.
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
      className="border-b border-border bg-canvas/70 text-body"
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-2.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm">
        <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-accent shrink-0">
          [ hosted preview ]
        </span>
        <span className="leading-relaxed">
          Recorded run, not a live AXL mesh. Spin-up clicks, run logs, and
          showcase artefacts replay fixtures. Run{" "}
          <code className="rounded bg-surface px-1.5 py-0.5 font-mono text-[0.85em] text-ink">
            make demo
          </code>{" "}
          for the real thing.
        </span>
        <span className="ml-auto flex items-center gap-3 shrink-0">
          <Link
            href="/docs#run-it-locally"
            className="text-xs font-medium text-accent hover:underline"
          >
            Run it locally &rarr;
          </Link>
          <Link
            href="https://github.com/vrnvrn/hacksim"
            target="_blank"
            rel="noreferrer"
            className="text-xs font-medium text-body hover:text-ink"
          >
            Repo
          </Link>
        </span>
      </div>
    </aside>
  );
}
