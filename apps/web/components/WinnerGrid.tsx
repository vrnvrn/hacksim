"use client";

import { useState } from "react";
import type { Bounty, Project, Snapshot } from "@/lib/types";
import { rankWinners } from "@/lib/api";
import { WinnerCard } from "./WinnerCard";
import { ProjectDemoModal } from "./ProjectDemoModal";
import { EmptyState } from "./EmptyState";
import Link from "next/link";

export function WinnerGrid({ snapshot }: { snapshot: Snapshot }) {
  const [openProjectId, setOpenProjectId] = useState<string | null>(null);
  const winnersByBounty = rankWinners(snapshot);

  const flat: Array<{ project: Project; rank: 1 | 2 | 3; bounty: Bounty }> = [];
  for (const bounty of snapshot.bounties) {
    const entries = winnersByBounty.get(bounty.id) ?? [];
    for (const e of entries) {
      flat.push({ project: e.project, rank: e.rank, bounty });
    }
  }

  if (flat.length === 0) {
    return (
      <EmptyState
        title="No qualifying submissions"
        body="No project met the rubric. Try a different prompt or run the sim again with more builders."
        cta={
          <Link
            href="/"
            className="rounded-md bg-accent text-white px-5 py-2.5 font-semibold hover:opacity-90 transition"
          >
            Run another simulation
          </Link>
        }
      />
    );
  }

  const open = (id: string) => setOpenProjectId(id);
  const close = () => setOpenProjectId(null);

  const openProject = snapshot.projects.find((p) => p.id === openProjectId) ?? null;
  const openBounty = openProject
    ? snapshot.bounties.find((b) => b.id === openProject.bounty_id)
    : undefined;

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-4 gap-y-12">
        {flat.map(({ project, rank, bounty }) => (
          <WinnerCard
            key={`${bounty.id}-${project.id}`}
            project={project}
            rank={rank}
            prize={bounty}
            onTryIt={() => open(project.id)}
          />
        ))}
      </div>
      {openProjectId ? (
        <ProjectDemoModal
          simId={snapshot.id}
          projectId={openProjectId}
          open
          onClose={close}
          project={openProject ?? undefined}
          bounty={openBounty}
          builders={snapshot.builders}
          judges={snapshot.judges}
          verdicts={snapshot.verdicts}
        />
      ) : null}
    </>
  );
}
