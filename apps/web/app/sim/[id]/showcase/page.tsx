import Link from "next/link";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { StatPill } from "@/components/StatPill";
import { WinnerGrid } from "@/components/WinnerGrid";
import { headers } from "next/headers";
import { notFound } from "next/navigation";
import type { Snapshot } from "@/lib/types";

async function loadSnapshot(simId: string): Promise<Snapshot> {
  const h = await headers();
  const host = h.get("x-forwarded-host") ?? h.get("host") ?? "localhost:3000";
  const proto = h.get("x-forwarded-proto") ?? "http";
  const useMocks = process.env.NEXT_PUBLIC_USE_MOCKS === "true";
  const path = useMocks
    ? `/api/mocks/snapshot?id=${encodeURIComponent(simId)}`
    : `/api/sim/${encodeURIComponent(simId)}/snapshot`;
  const res = await fetch(`${proto}://${host}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`snapshot ${res.status}`);
  return (await res.json()) as Snapshot;
}

const formatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

export default async function ShowcasePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let snapshot: Snapshot;
  try {
    snapshot = await loadSnapshot(id);
  } catch {
    notFound();
  }

  const totalPool = snapshot.bounties.reduce(
    (s, b) => s + b.prize_amount_usd,
    0,
  );
  const submitted = snapshot.projects.filter(
    (p) => p.status === "submitted" || p.status === "judged",
  ).length;

  return (
    <>
      <Nav />
      <main className="max-w-7xl mx-auto px-6 lg:px-8 pt-10 pb-24">
        <header className="mb-16">
          <p className="text-xl text-body italic max-w-2xl leading-snug">
            &ldquo;{snapshot.prompt}&rdquo;
          </p>
          <h1 className="font-display text-5xl lg:text-6xl font-semibold text-ink mt-6 leading-tight">
            Showcase
          </h1>
          <div className="mt-6 flex flex-wrap items-center gap-2">
            <StatPill
              label={`Pool ${formatter.format(totalPool)}`}
              tone="accent"
            />
            <StatPill
              label={`${snapshot.builders.length} agents`}
              tone="muted"
            />
            <StatPill label={`${submitted} submissions`} tone="muted" />
          </div>
        </header>

        <WinnerGrid snapshot={snapshot} />

        <div className="mt-24 text-center">
          <Link
            href="/"
            className="rounded-full border-2 border-ink bg-surface text-ink px-8 py-3 font-semibold hover:bg-ink hover:text-surface transition"
          >
            Run another simulation
          </Link>
        </div>
      </main>
      <Footer />
    </>
  );
}
