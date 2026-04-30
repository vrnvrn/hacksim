# 40. Example tiles spin up real sims instead of linking to a stale id

## What changed

Every "Example runs" card on the home page (and the standalone
`/examples` page) used to link to a hardcoded sim id
(`/sim/sim_2026-04-28_a1b2c3#submissions`). Under the default demo
configuration (`NEXT_PUBLIC_USE_MOCKS=false`), the orchestrator never
served that id, so the live page hit `notFound()` and rendered a
Next.js 404. Every example link was a dead end.

Each card now `POST`s its associated prompt to `/api/sim` on click and
redirects to the freshly created sim id. The pattern matches
`HeroExamplesAside`, which was already doing this for the four small
preset cards next to the prompt input.

Files added:

- `apps/web/components/ExampleCard.tsx`: client wrapper around
  `ProjectTile` that submits the per-card prompt and redirects to the
  new sim. Surfaces a "Could not reach the orchestrator" inline error
  instead of redirecting to the dead canned id.

Files changed:

- `apps/web/components/HeroExamples.tsx`: the four `EXAMPLES` entries
  swap `href` for `prompt`. Each prompt is themed to make a sim that
  could plausibly produce the project on the tile (D3 visualisation,
  three.js mesh demo, EIP-2612 onchain game, AI-evals tooling). A
  small explanatory line under the heading tells the user that the
  tile copy is illustrative and each run produces its own projects.
- `apps/web/components/HeroExamplesAside.tsx`: the same canned-mock
  fallback is removed; on POST failure, the aside surfaces an inline
  error inside the card rather than redirecting the user to a 404.
- `apps/web/app/examples/page.tsx`: copy update, "Pre-recorded
  simulations. Each run is reproducible..." swapped for "Click any
  card to spin up a fresh sim with that prompt." (the prior copy was
  out of step with the new behaviour and never matched the truth).

## Why

The judge review caught it: judges click examples; they get 404s. The
old links were a hardcoded mock-mode contract; flipping
`NEXT_PUBLIC_USE_MOCKS=true` made them work, but make demo runs with
mocks off. Spinning up a real sim per click matches the home page's
own primary CTA path and turns every example into a working demo
instead of a dead end.

## How to verify

```
cd apps/web && pnpm test --run
cd apps/web && pnpm exec tsc --noEmit
```

Tests pass. Manual: `make demo`, click any "Example runs" card, watch
the URL transition to a fresh `/sim/<new-id>` and the live page
populate. Stop the orchestrator, click a card, the inline error
appears in the card with no redirect.

## Gensyn surface used

None directly. The example click hits the orchestrator's
`POST /api/sim`, which does start the AXL stack underneath, so the
tile is now an end-to-end on-ramp into the mesh.

## Up next

Sweep stale doc links to the canned sim id. The `/sim/sim_2026-...`
URL is no longer reachable in the default demo path; references in
process notes and the README screenshot caption should switch to
generic `/sim/<id>` placeholders.
