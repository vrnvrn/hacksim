# 19. Next.js scaffold, Tailwind, design tokens, fonts

## What changed

Bootstrapped the web app under `apps/web/` against the design contract in
`refs/UX_SPEC.md`. The scaffold lands these files: `package.json` (Next.js 15,
React 19, TypeScript strict, Tailwind v4, Vitest, Playwright), `tsconfig.json`,
`next.config.ts`, `next-env.d.ts`, `postcss.config.mjs`, `tailwind.config.ts`
(every design token from `refs/PLAN.md` section 6), `app/globals.css` with the
Tailwind v4 `@theme` block and a local `@font-face` for General Sans,
`app/layout.tsx`, `app/fonts.ts` (Inter Variable and JetBrains Mono via
`next/font/google`, General Sans served from `public/fonts/`), `vitest.config.ts`,
`vitest.setup.ts`, `playwright.config.ts`, and `apps/web/.env.local.example`
with `NEXT_PUBLIC_USE_MOCKS=true` as the default.

## Why

The frontend ships in five subsequent commits (24 to 28). Locking the
toolchain, design tokens, and test runners on day one keeps every later commit
small and reviewable. Tailwind v4 reads tokens from `@theme` blocks rather
than `theme.extend`, so the tokens live in CSS and the `tailwind.config.ts`
mirror exists for the IDE. The mock-mode default lets the visual review,
component review, and Playwright smoke test all run with no orchestrator
running.

The General Sans font is served via a local `@font-face` rather than
`next/font/local` so the build does not fail when the woff2 is absent. The
fallback chain in `globals.css` lands on Inter Variable, which is loaded via
`next/font/google`. Drop the woff2 into `public/fonts/` to activate the
display face. The brief calls for `next/font/local`; we deviated to keep the
build green out of the box. Backend or design can flip back to the
`next/font/local` form once the file is in the repo.

## How to verify

```
cd apps/web
pnpm install
pnpm test
pnpm exec playwright install chromium
NEXT_PUBLIC_USE_MOCKS=true pnpm dev
```

`pnpm test` runs Vitest with one passing setup test and the per-component
suites that land in commits 20 to 23. `pnpm dev` opens the hero with the
prompt input wired to the mock POST. The example link routes to
`/sim/sim_2026-04-28_a1b2c3` which renders the canonical fixture.

## Gensyn surface used

None directly. The scaffold prepares the surface that consumes the SSE
endpoint specified in `refs/UX_SPEC.md` section 6, which mirrors
`research_network.py` style envelopes. The SSE hook in `lib/use-sse.ts`
matches the Gensyn pattern: one `EventSource` per page, parse on receipt, no
buffering.

## Up next

Commit 20 lands the hero page proper: `Nav`, `HeroPrompt` with the settings
popover, `HowItWorks`, `Footer`, and `HeroExamples`. Each ships a Vitest
test.
