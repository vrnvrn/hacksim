import type { Snapshot } from "@/lib/types";

/**
 * Plain-English description of what the simulation is doing right now,
 * driven by the live snapshot. Server-rendered. The page's RefreshTicker
 * re-runs the parent every 2.5 s so this banner stays current without
 * client-side state.
 *
 * Phase counter:
 *   0 BOUNTY_DESIGN, 1 TEAM_FORMATION, 2 BUILD, 3 JUDGING, 4 SHOWCASE.
 *
 * The mesh is real. Every count below comes from envelopes that crossed
 * the AXL mesh and were folded into the orchestrator's snapshot.
 */
export function NowHappening({ snapshot }: { snapshot: Snapshot }) {
  const cfg = snapshot.config;
  const designers = cfg?.designers ?? 0;
  const builders = cfg?.builders ?? snapshot.builders.length;
  const judges = cfg?.judges ?? 0;
  const expectedVerdicts = judges * snapshot.projects.length;

  const { headline, detail } = describe({
    phase: snapshot.phase,
    designers,
    builders,
    judges,
    bounties: snapshot.bounties.length,
    teams: snapshot.teams.length,
    projects: snapshot.projects.length,
    verdicts: snapshot.verdicts.length,
    expectedVerdicts,
    closed: snapshot.phase >= 4,
  });

  return (
    <div
      className="rounded-2xl border border-border bg-canvas/60 px-5 py-4"
      role="status"
      aria-live="polite"
    >
      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-accent">
        [ now happening ]
      </p>
      <p className="mt-1 text-lg font-semibold text-ink leading-snug">
        {headline}
      </p>
      {detail ? (
        <p className="mt-1 text-sm text-body leading-relaxed">{detail}</p>
      ) : null}
    </div>
  );
}

function describe(s: {
  phase: number;
  designers: number;
  builders: number;
  judges: number;
  bounties: number;
  teams: number;
  projects: number;
  verdicts: number;
  expectedVerdicts: number;
  closed: boolean;
}): { headline: string; detail?: string } {
  if (s.phase === 0) {
    if (s.bounties === 0) {
      return {
        headline: `${plural(s.designers, "sponsor agent")} are drafting bounties.`,
        detail:
          "Each sponsor has its own peer id, its own opinion, and its own AXL node. Bounties land on the mesh as bounty.posted envelopes.",
      };
    }
    if (s.bounties < s.designers) {
      return {
        headline: `${plural(s.designers, "sponsor")} drafting bounties (${s.bounties} of ${s.designers} posted).`,
        detail: "Builders are queued up; they pick once every sponsor has posted.",
      };
    }
    return {
      headline: `${s.designers} sponsors posted ${s.bounties} bounties.`,
      detail: "Builders pick a bounty next.",
    };
  }

  if (s.phase === 1) {
    return {
      headline: `${plural(s.builders, "builder")} are reading the bounties and forming teams.`,
      detail:
        s.teams > 0
          ? `${plural(s.teams, "team")} formed so far. The builders pick a bounty that fits their skill profile, then broadcast team.formed.`
          : "Builders pick a bounty that fits their skill profile, then broadcast team.formed.",
    };
  }

  if (s.phase === 2) {
    if (s.projects === 0) {
      return {
        headline: `${plural(s.builders, "builder")} are writing their projects.`,
        detail:
          "Each builder writes a real index.html plus app.js and style.css into its own working tree, git-commits, then broadcasts project.submitted with the commit hash.",
      };
    }
    return {
      headline: `Builders are submitting (${s.projects} of ${s.builders} ${maybeS(s.builders, "project")} in).`,
      detail: "The orchestrator git-archives each submission and serves it under a strict CSP so the showcase can iframe it.",
    };
  }

  if (s.phase === 3) {
    if (s.verdicts === 0) {
      return {
        headline: `${plural(s.judges, "judge")} are reviewing every submission.`,
        detail:
          "Each judge writes its own rubric, opens the projects, and broadcasts verdict.published per project.",
      };
    }
    if (s.expectedVerdicts > 0 && s.verdicts < s.expectedVerdicts) {
      return {
        headline: `Judging in progress (${s.verdicts} of ${s.expectedVerdicts} scores in).`,
        detail: `${plural(s.judges, "judge")} reviewing ${plural(s.projects, "submission")}.`,
      };
    }
    return {
      headline: `Judging complete. ${plural(s.verdicts, "verdict")} cast across ${plural(s.projects, "project")}.`,
      detail: "The organiser is tallying the leaderboard.",
    };
  }

  // Phase 4: SHOWCASE.
  if (s.projects === 0) {
    return {
      headline: "Hackathon closed. No submissions made it through.",
      detail:
        "Try the smoke pace next time, or click an example. The mesh propagation depends on local timing.",
    };
  }
  return {
    headline: `Hackathon closed. ${plural(s.projects, "project")} ranked.`,
    detail: "Open the showcase to read the leaderboard and play with the winners.",
  };
}

function plural(n: number, noun: string): string {
  return `${n} ${maybeS(n, noun)}`;
}

function maybeS(n: number, noun: string): string {
  return n === 1 ? noun : `${noun}s`;
}
