# 21. Live page, BountyCard, BuilderRoster, ProjectTile, JudgePanel

## What changed

Built the live page at `apps/web/app/sim/[id]/page.tsx`. The page is a
Server Component that fetches the snapshot via `getSnapshot` and renders five
sections in order: Bounties, Builders, Submissions, Judges, Verdicts. The
right-rail is reserved for the run log (commit 22 plumbs it).

Components added: `BountyCard.tsx`, `BuilderChip.tsx`, `BuilderRoster.tsx`,
`ProjectTile.tsx`, `JudgePanel.tsx`, `Verdicts.tsx`, `PhasePill.tsx`.
`SubmissionsGrid.tsx` is a client island that owns the modal-open state for
the project tiles. Each component ships its `<Component>.test.tsx` and a
default-state snapshot.

Added the snapshot fixture at `apps/web/lib/mocks/snapshot.json`, a
phase-3 sim with five bounties, six builders, three teams, three submitted
projects, three judges, and nine verdicts. The mock route at
`apps/web/app/api/mocks/snapshot/route.ts` reads the fixture per request so
the file can be edited live.

## Why

The live page is a static-feeling product page that animates as envelopes
arrive on the SSE stream. The SSR pass renders the snapshot at the moment of
visit; the SSE stream patches the page in commit 22. Splitting the work in
two commits keeps each test focused and lets a reviewer check the
non-streaming path on its own.

The Submissions grid is where the "playable" part of HackSim lives. Each
tile has a "Try it" button that opens the `ProjectDemoModal`. The modal
itself lands in commit 23; the wiring lands here so the integration is
testable end to end as soon as the modal exists.

## How to verify

```
cd apps/web
pnpm test components/BountyCard.test.tsx components/ProjectTile.test.tsx components/JudgePanel.test.tsx components/BuilderRoster.test.tsx components/PhasePill.test.tsx
NEXT_PUBLIC_USE_MOCKS=true pnpm dev
```

Open `http://localhost:3000/sim/sim_2026-04-28_a1b2c3`. The five sections
populate from the fixture. The phase pill reads "Phase: judging" because the
snapshot is at phase 3.

## Gensyn surface used

The page consumes the snapshot shape that the orchestrator derives from
in-memory state (built up from broadcast envelopes received via
`research_network.py` style `/recv` polling). The snapshot endpoint shape is
the contract documented in `refs/UX_SPEC.md` section 6.

## Up next

Commit 22 lands `RunLog.tsx` and `lib/use-sse.ts`, the SSE client. The run
log mounts on the right rail of the live page. The mock SSE endpoint
replays `apps/web/lib/mocks/stream.ndjson` at 1.5x real time.
