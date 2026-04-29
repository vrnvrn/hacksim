# 24. Showcase page with winner ribbons, Playwright smoke test

## What changed

Built the showcase page at `apps/web/app/sim/[id]/showcase/page.tsx`. The
page is server-rendered: the snapshot is fetched on the server (mock or
real), winners are ranked per bounty by average verdict total, and a flat
grid of `WinnerCard.tsx` components renders. Each card has a coloured
ribbon (gold for first, silver for second, coral for third) and a "Try it"
button that opens the same `ProjectDemoModal` from commit 23. A
"Run another simulation" CTA at the bottom routes back to `/`.

`WinnerCard.tsx` and `WinnerGrid.tsx` are new. `WinnerGrid.tsx` is a
client island that owns the modal-open state for the showcase ribbons.
When no project clears the rubric, the grid renders an `EmptyState` with a
CTA back to `/`.

Playwright smoke test at `apps/web/tests/playwright/smoke.spec.ts`. Two
specs:

1. From `/`, fill the prompt, submit, land on `/sim/<id>`, open the first
   submission's `ProjectDemoModal`, switch through Demo, Code, Verdict
   tabs, verify the iframe sandbox attribute, close the modal.
2. From `/sim/sim_2026-04-28_a1b2c3/showcase`, verify the heading, click
   the first winner's "Try it" button, verify the Demo tab shows.

## Why

The showcase page is the URL a reviewer shares. It needs to render fully
from the server with no client hydration before the data appears. Sharing
the URL alone should land on a complete, scroll-from-top, click-to-play
page. The empty state handles the legitimate "nobody won" case without
breaking the flow.

The Playwright test guards every commit from 23 forward against the kind
of regression that breaks the demo path: the prompt input, the route to
the live page, the modal opening, the tabs switching, the iframe sandbox
attribute. One spec covers the live path; one covers the showcase path.

## How to verify

```
cd apps/web
pnpm test
pnpm exec playwright install chromium
pnpm exec playwright test
```

The Vitest suites for every component pass. The Playwright suite boots the
dev server in mock mode, opens a Chromium window, walks the hero to the
modal, and closes the modal. Both specs go green in under a minute.

## Gensyn surface used

The showcase consumes the same snapshot shape as the live page. The winner
ranking lives in `apps/web/lib/api.ts` and operates on the snapshot's
`projects[]` and `verdicts[]`. The orchestrator computes the same ranking
server-side in `packages/agents/organiser/` (commit 21) for the leaderboard
endpoint; the frontend re-derives it for offline-friendly rendering.

## Up next

The frontend is feature-complete behind the mock flag. The integration step
is flipping `NEXT_PUBLIC_USE_MOCKS=false` once the orchestrator (commits 22
and earlier) is running. The hand-off checklist in
`refs/UX_SPEC.md` section 13 lists every backend endpoint that must match
shape before integration.
