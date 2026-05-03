# 72. RunLog pins to bottom; live page boot banner stays visible through spawn

## What changed

Three small frontend fixes that together close the demo-readiness UX
loop the user flagged after the first dry run.

**RunLog auto-scrolls to the bottom on every new event.**
`apps/web/components/RunLog.tsx` previously used a "scroll only if
the user is within 1.5 screens of the bottom" heuristic. Under fast
bursts (the AXL mesh boot fans out 14 envelopes in roughly the same
second), the heuristic measured the container before the new lines
laid out and decided the user was scrolled up, freezing the pane at
the top of the burst. The new effect always pins `scrollTop =
scrollHeight` on every lines change unless `paused` is true. Users
who want to scroll back hit the existing Pause toggle, which freezes
auto-scroll without dropping events.

**Live page boot banner stays visible through the full spawn
window.** `apps/web/components/NowHappening.tsx` previously gated the
"Booting the AXL mesh" branch on `builderCount === 0`, so the very
first `builder.registered` event flipped the banner to "Sponsor
agents are drafting their bounties" while the other thirteen nodes
were still coming up. The boot branch now stays visible until every
configured builder has registered (`builderCount < builders`) and
shows a live counter ("3 of 8 builders registered so far") plus the
total node count derived from the config. The total includes the
organiser, every designer, every builder, and every judge, so it
matches the actual subprocess count instead of a hardcoded 15.

**Hero button text matches the new banner copy.**
`apps/web/components/HeroPrompt.tsx` swaps "Spinning up 15 AXL
nodes..." for "Spinning up AXL mesh..." so the spinner stops
pretending the population is fixed at 15 (it is configurable via
Settings).

## Why

Every part of this commit is a UX detail the user surfaced from the
first demo dry run. The prompt-plumbing fix in process note 71 made
the bounty cards readable; these three changes make the live-page
choreography readable too. Specifically:

- The run log is the most direct evidence that the AXL mesh is
  doing real work. If it freezes mid-burst, a viewer sees "Booting
  the agents..." and assumes the demo wedged. Pinning to the bottom
  removes the failure mode entirely.
- The boot banner needs to stay visible for the full ten-second
  spawn window so a viewer who clicked Spin up sim sees "Spinning up
  the AXL mesh" before the bounty cards appear, rather than a brief
  flicker through three different labels.
- The hardcoded 15 was technically wrong on the smaller smoke
  population (1 + 1 + 3 + 1 = 6) and on any custom Settings dial.

## How to verify

- `pnpm vitest --run` reports 94 passed across 27 files (no test
  references the old strings; the snapshot test on Hero passes
  unchanged because it does not render the pending-state copy).
- Manual: `make demo`, click Spin up sim. The button reads
  "Spinning up AXL mesh...". The redirect to /sim/<id> is immediate.
  The banner reads "Spinning up the AXL mesh" and lists 0 of 8
  builders, then 3 of 8, then 8 of 8 before flipping to "Sponsor
  agents are drafting their bounties". The run log fills from the
  bottom and stays pinned as new events arrive.

## Gensyn surface used

None. All three are browser-side rendering tweaks.

## Up next

This closes the user-facing UX loop for the demo. The remaining
items in `refs/DEMO_READINESS.md` are the Anthropic rate limit
(documented, accepted) and the cosmetic envelope.unhandled noise.

## Files

`apps/web/components/RunLog.tsx`,
`apps/web/components/NowHappening.tsx`,
`apps/web/components/HeroPrompt.tsx`,
`docs/process/72-runlog-autoscroll-and-boot-banner.md`.
