"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import type {
  Bounty,
  Builder,
  Judge,
  Project,
  Verdict,
} from "@/lib/types";
import { ProjectTile } from "./ProjectTile";
import { ProjectDemoModal } from "./ProjectDemoModal";

// Live-page Submissions section. Owns the ProjectDemoModal state so each tile
// can request "open me" without prop-drilling through the page.
export function SubmissionsGrid({
  simId,
  projects,
  bounties,
  builders,
  judges,
  verdicts,
}: {
  simId: string;
  projects: Project[];
  bounties: Bounty[];
  builders: Builder[];
  judges: Judge[];
  verdicts: Verdict[];
}) {
  const [openProjectId, setOpenProjectId] = useState<string | null>(null);
  const open = (id: string) => setOpenProjectId(id);
  const close = () => setOpenProjectId(null);

  const openProject = projects.find((p) => p.id === openProjectId) ?? null;
  const openBounty = openProject
    ? bounties.find((b) => b.id === openProject.bounty_id)
    : undefined;

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-4 gap-y-8">
        {projects.map((p) => (
          <motion.div
            key={p.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
          >
            <ProjectTile project={p} onTryIt={open} />
          </motion.div>
        ))}
      </div>
      {openProjectId ? (
        <ProjectDemoModal
          simId={simId}
          projectId={openProjectId}
          open
          onClose={close}
          project={openProject ?? undefined}
          bounty={openBounty}
          builders={builders}
          judges={judges}
          verdicts={verdicts}
        />
      ) : null}
    </>
  );
}
