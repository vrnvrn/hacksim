import Link from "next/link";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { BountyCard } from "@/components/BountyCard";
import { BuilderRoster } from "@/components/BuilderRoster";
import { JudgePanel } from "@/components/JudgePanel";
import { Verdicts } from "@/components/Verdicts";
import { StatPill } from "@/components/StatPill";
import { PhasePill } from "@/components/PhasePill";
import { RunLog } from "@/components/RunLog";
import { SubmissionsGrid } from "@/components/SubmissionsGrid";
import { getSnapshot } from "@/lib/api";
import { headers } from "next/headers";
import { notFound } from "next/navigation";
import type { Snapshot } from "@/lib/types";

async function loadSnapshot(simId: string): Promise<Snapshot> {
  // In RSC the relative URL needs a host. We resolve via the request headers
  // so dev (localhost) and production (hacksim.app) both work.
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

export default async function SimPage({
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

  return (
    <>
      <Nav />
      <main className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-x-8 max-w-7xl mx-auto px-6 lg:px-8 pt-10 pb-24">
        <div className="min-w-0">
          <header className="mb-12">
            <p className="text-xl text-body italic max-w-2xl leading-snug">
              &ldquo;{snapshot.prompt}&rdquo;
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <StatPill label={`${snapshot.builders.length} agents`} tone="muted" />
              <StatPill
                label={`${snapshot.bounties.length} bounties`}
                tone="muted"
              />
              <PhasePill phase={snapshot.phase} />
              {snapshot.phase >= 4 ? (
                <Link
                  href={`/sim/${id}/showcase`}
                  className="ml-2 text-sm font-semibold text-accent hover:underline"
                >
                  View showcase
                </Link>
              ) : null}
            </div>
          </header>

          <Section id="bounties" title="Bounties">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {snapshot.bounties.map((b) => (
                <BountyCard key={b.id} bounty={b} />
              ))}
            </div>
          </Section>

          <Section id="builders" title="Builders">
            <BuilderRoster builders={snapshot.builders} />
          </Section>

          <Section id="submissions" title="Submissions">
            <SubmissionsGrid
              simId={snapshot.id}
              projects={snapshot.projects}
              bounties={snapshot.bounties}
              builders={snapshot.builders}
              judges={snapshot.judges}
              verdicts={snapshot.verdicts}
            />
          </Section>

          <Section id="judges" title="Judges">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {snapshot.judges.map((j) => (
                <JudgePanel key={j.peer_id} judge={j} />
              ))}
            </div>
          </Section>

          {snapshot.phase >= 3 ? (
            <Section id="verdicts" title="Verdicts">
              <Verdicts verdicts={snapshot.verdicts} />
            </Section>
          ) : null}
        </div>

        <div className="lg:sticky lg:top-20 self-start">
          <RunLog simId={snapshot.id} />
        </div>
      </main>
      <Footer />
    </>
  );
}

function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-heading`}
      className="mt-12 first:mt-0"
    >
      <h2
        id={`${id}-heading`}
        className="font-display text-3xl font-semibold text-ink mb-6"
      >
        {title}
      </h2>
      {children}
    </section>
  );
}
