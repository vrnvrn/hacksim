import Link from "next/link";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";

/**
 * Renders for any route that calls `notFound()`. The most common landing
 * here is /sim/<dead-id> after the orchestrator has moved on (one sim at
 * a time policy). Bare Next.js 404 reads as broken; this page reads as
 * "the sim is gone, here is what to do next."
 */
export default function NotFound() {
  return (
    <>
      <Nav />
      <main
        className="max-w-3xl mx-auto px-6 lg:px-8 pt-20 pb-24 text-center"
        role="main"
      >
        <p className="text-xs font-mono uppercase tracking-[0.18em] text-accent">
          [ 404 . sim not found ]
        </p>
        <h1 className="font-display text-4xl lg:text-5xl font-semibold text-ink mt-4 leading-tight">
          That simulation has moved on.
        </h1>
        <p className="text-base lg:text-lg text-body mt-5 max-w-xl mx-auto leading-relaxed">
          HackSim runs one simulation at a time per orchestrator process,
          so an older sim id stops resolving the moment a new one spins
          up. The recorded fixtures live behind their own canned id;
          everything else is ephemeral.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/"
            className="rounded-md px-5 py-2.5 bg-accent text-white text-sm font-semibold hover:opacity-90 transition"
          >
            Spin up a new sim
          </Link>
          <Link
            href="/examples"
            className="rounded-full border-2 border-ink bg-surface text-ink px-5 py-2.5 text-sm font-semibold hover:bg-ink hover:text-surface transition"
          >
            Pick an example run
          </Link>
          <Link
            href="/docs#run-it-locally"
            className="text-sm font-medium text-body hover:text-ink transition"
          >
            Run it locally &rarr;
          </Link>
        </div>
      </main>
      <Footer />
    </>
  );
}
