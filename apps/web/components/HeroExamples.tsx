import Link from "next/link";
import type { Project } from "@/lib/types";
import { ExampleCard } from "./ExampleCard";

// Four example sims. Each card POSTs its prompt to /api/sim on click and
// redirects to the freshly-spun sim id. The Project payload here is just
// preview copy for the tile; the actual projects are produced by the run.
const EXAMPLES: Array<{ project: Project; prompt: string }> = [
  {
    prompt:
      "a developer tooling hackathon for visualisations of agent activity and team formation, four sponsors and a $4k pool",
    project: {
      id: "proj_d3vis",
      team_id: "team_alpha",
      bounty_id: "bnty_1",
      title: "Tree of Skill",
      tagline: "A D3 force graph of every builder, coloured by skill cluster.",
      description:
        "A live force-directed graph that pulses on every team-formed event and recolours when a builder changes track.",
      status: "judged",
      submitted_at: "2026-04-28T12:30:00Z",
      commit_hash: "1a2b3c4d5e6f7890",
      entry_path: "index.html",
      artefact_path: "/served/proj_d3vis",
      github_url: null,
    },
  },
  {
    prompt:
      "a peer-to-peer demo hackathon for three.js scenes that visualise live mesh traffic, three sponsors",
    project: {
      id: "proj_threejs",
      team_id: "team_beta",
      bounty_id: "bnty_2",
      title: "Mesh Cathedral",
      tagline: "A three.js scene where each peer is a glowing column on the floor.",
      description:
        "Walk the cathedral. Each column lights up when its peer broadcasts. The room hums in proportion to mesh traffic.",
      status: "judged",
      submitted_at: "2026-04-28T12:35:00Z",
      commit_hash: "abcdef0123456789",
      entry_path: "index.html",
      artefact_path: "/served/proj_threejs",
      github_url: null,
    },
  },
  {
    prompt:
      "an onchain games hackathon focused on EIP-2612 permits, five sponsors and a $5k pool",
    project: {
      id: "proj_game",
      team_id: "team_gamma",
      bounty_id: "bnty_3",
      title: "Permit Pong",
      tagline: "Pong, but each rally is a signed permit.",
      description:
        "A two-paddle pong where every paddle hit triggers an EIP-2612 permit. You watch the ball, you watch the signatures.",
      status: "judged",
      submitted_at: "2026-04-28T12:40:00Z",
      commit_hash: "fedcba9876543210",
      entry_path: "index.html",
      artefact_path: "/served/proj_game",
      github_url: null,
    },
  },
  {
    prompt:
      "an AI evals hackathon for tools to compare and explain judge rubrics, three sponsors",
    project: {
      id: "proj_rubric",
      team_id: "team_delta",
      bounty_id: "bnty_4",
      title: "Rubric Diff",
      tagline: "Visualise how three judges weighted the same project differently.",
      description:
        "A small chart per project showing each judge's weighted scores side by side. Click any bar to read the rationale.",
      status: "judged",
      submitted_at: "2026-04-28T12:50:00Z",
      commit_hash: "0a1b2c3d4e5f6789",
      entry_path: "index.html",
      artefact_path: "/served/proj_rubric",
      github_url: null,
    },
  },
];

export function HeroExamples() {
  return (
    <section
      aria-labelledby="examples-heading"
      className="mt-24 max-w-7xl mx-auto px-6 lg:px-8"
    >
      <div className="flex items-baseline justify-between">
        <h2
          id="examples-heading"
          className="font-display text-3xl lg:text-4xl font-semibold text-ink"
        >
          Example runs
        </h2>
        <Link
          href="/examples"
          className="text-sm font-medium text-body hover:text-ink transition"
        >
          See all
        </Link>
      </div>
      <p className="text-sm text-muted mt-3 max-w-2xl">
        Click any card to spin up a fresh sim with that prompt. The titles
        and taglines are illustrative; every run produces its own projects.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-x-4 gap-y-12 mt-10">
        {EXAMPLES.map(({ project, prompt }) => (
          <ExampleCard key={project.id} project={project} prompt={prompt} />
        ))}
      </div>
    </section>
  );
}
