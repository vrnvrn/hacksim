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
import { NowHappening } from "@/components/NowHappening";
import { SubmissionsGrid } from "@/components/SubmissionsGrid";
import { headers } from "next/headers";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import type { Snapshot } from "@/lib/types";

// `/replay/<runId>` renders the same shape as `/sim/<id>` but reads from
// the replay endpoints. The orchestrator's recorder writes one JSONL
// file per sim; this page loads the accumulated final snapshot and
// streams the recorded SSE feed at 4x cadence so a judge can see a
// real run end to end without a local install.

export async function generateMetadata({
  params,
}: {
  params: Promise<{ runId: string }>;
}): Promise<Metadata> {
  const { runId } = await params;
  return { title: `HackSim · replay · ${runId}` };
}

async function loadSnapshot(runId: string): Promise<Snapshot> {
  const h = await headers();
  const host = h.get("x-forwarded-host") ?? h.get("host") ?? "localhost:3000";
  const proto = h.get("x-forwarded-proto") ?? "http";
  const path = `/api/replay/${encodeURIComponent(runId)}/snapshot`;
  const res = await fetch(`${proto}://${host}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`replay snapshot ${res.status}`);
  return (await res.json()) as Snapshot;
}

export default async function ReplayPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  let snapshot: Snapshot;
  try {
    snapshot = await loadSnapshot(runId);
  } catch {
    notFound();
  }

  return (
    <>
      <Nav />
      <main className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-x-8 max-w-7xl mx-auto px-6 lg:px-8 pt-10 pb-24">
        <div className="min-w-0">
          <header className="mb-12 space-y-5">
            <Link
              href="/"
              className="inline-flex items-center gap-1 text-xs font-mono uppercase tracking-[0.16em] text-muted hover:text-ink transition"
            >
              &larr; back to home
            </Link>
            <p className="text-xl text-body italic max-w-2xl leading-snug">
              &ldquo;{snapshot.prompt}&rdquo;
            </p>
            <NowHappening snapshot={snapshot} />
            <div className="flex flex-wrap items-center gap-2">
              <StatPill label="recorded run" tone="muted" />
              <StatPill label={`${snapshot.builders.length} agents`} tone="muted" />
              <StatPill label={`${snapshot.bounties.length} bounties`} tone="muted" />
              <StatPill label={`${snapshot.projects.length} projects`} tone="muted" />
              <StatPill label={`${snapshot.verdicts.length} verdicts`} tone="muted" />
              <PhasePill phase={snapshot.phase} />
            </div>
            <p className="text-sm text-muted max-w-2xl leading-relaxed">
              You are watching a previously recorded run streamed at four
              times original speed. Every event below is the byte the
              orchestrator captured live; nothing is mocked.
            </p>
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

          <Section
            id="submissions"
            title="Submissions"
            caption="Click any tile to play the project the agents built. Each demo runs in a sandboxed iframe with no network access."
          >
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
          <RunLog simId={runId} mode="replay" />
        </div>
      </main>
      <Footer />
    </>
  );
}

function Section({
  id,
  title,
  caption,
  children,
}: {
  id: string;
  title: string;
  caption?: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-heading`} className="mt-12 first:mt-0">
      <h2 id={`${id}-heading`} className="font-display text-3xl font-semibold text-ink">
        {title}
      </h2>
      {caption ? (
        <p className="text-sm text-body mt-2 mb-6 max-w-2xl leading-relaxed">{caption}</p>
      ) : (
        <div className="mb-6" />
      )}
      {children}
    </section>
  );
}
