# 31. Hero redesign: compact above-fold and side example panel

## What changed

Reworks the landing page so the prompt input, primary CTAs, and four real-example shortcuts all fit above the fold on a 1440x900 laptop. Reviewers see the interactive surface immediately; users who do not want to type a prompt can click an example and watch a real sim spawn.

- `apps/web/app/page.tsx` switches the hero from a single-column tower to a `lg:grid-cols-[1fr_22rem]` two-column layout. Left column: a small `[ hacksim ]` mono label, the H1 (now `text-4xl md:text-5xl lg:text-6xl`, down from `text-6xl lg:text-8xl`), the description, and the prompt form. Right column: the new `HeroExamplesAside`. Stacks to one column below `lg:`.
- `apps/web/components/HeroExamplesAside.tsx` is new. Renders four preset cards (Onchain agents, Research lab, Indie agentic, Privacy primitives), each with a curated prompt, a gradient glyph thumbnail, and a click handler that POSTs `/api/sim` and routes the user straight to the live page. Falls back to the canned mock sim id if the orchestrator is unreachable so the click still does something visible.
- `apps/web/components/HeroPrompt.tsx` is tightened: textarea drops from `min-h-[140px] text-lg` to `min-h-[100px] text-base`, three rows tall by default. Buttons drop one size class. Top margin tightens.
- `apps/web/components/Nav.tsx` swaps plain link labels for `[ examples ]` `[ docs ]` `[ github ]` in mono caps, with a small accent diamond next to the wordmark. A nod to Gensyn's bracket aesthetic without going full retro.
- The previous large "Example runs" tile section below the fold (`HeroExamples`) is dropped from the home page; the aside replaces it because the aside is reachable without scrolling. The component file itself stays in the tree for reuse on other pages.
- Snapshot tests for Nav, Footer, HeroPrompt are regenerated to match the new markup. The Nav test now matches link text case-insensitively so the bracketed labels still pass without coupling tests to brand details.

## Why

User feedback after the first hero (commit 20):

1. The H1 dominated the viewport, pushing the prompt below the fold.
2. The hero should feel a touch more like Gensyn's own pages: dense, mono flourishes, brackets.
3. Examples were below the fold. A user not in the mood to type was one scroll away from any working content.

This commit addresses all three without losing our identity (white canvas, purple accent, Inter Variable for body, General Sans display fallback). Click-to-spin from the aside means the four examples are not decorative; they are entry points to live runs.

## How to verify

```
cd apps/web
pnpm test                     # 63 vitest tests pass
pnpm build                    # clean build, 0 warnings
pnpm dev                      # http://localhost:3000
```

Then in a 1440x900 viewport, confirm the prompt textarea and both CTAs are visible without scrolling, and the four example cards on the right are visible and clickable.

End-to-end (orchestrator + frontend, real spawn):

```
make demo
```

Click any of the four example cards on the right. The frontend POSTs `/api/sim` with the preset prompt, the orchestrator spawns a real population, and the browser routes to the new sim's live page. Within ~75 seconds (smoke pace) you see bounties, projects, judges, and a leaderboard populate.

## Gensyn surface used

None new. Pure UI work on top of the existing API contract.

## Up next

This is the last visual change before the judge review. Future copy or asset changes (a real logo, font swaps, dark mode) can land without touching the layout. The next deliverables are: a README pass that links the per-commit `docs/process/NN-*.md` series, and an optional Fly.io target for a hosted demo.
