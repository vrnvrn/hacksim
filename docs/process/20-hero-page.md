# 20. Hero page with prompt input and CTA pair

## What changed

Built the hero page (`apps/web/app/page.tsx`) plus its components: `Nav.tsx`,
`HeroPrompt.tsx` with the Settings popover, `HowItWorks.tsx`, `HeroExamples.tsx`
(four canned project tiles linked to the mock sim), and `Footer.tsx`. Added
`StatPill.tsx`, `EmptyState.tsx`, and the shared `lib/cn.ts` utility. Each
component lands with a `<Component>.test.tsx` that exercises render,
interaction, and a snapshot for the default state. A `POST /api/sim` route
proxies to the orchestrator in real mode and returns the canonical mock id in
mock mode.

## Why

The hero is the moment the user decides whether to spend two minutes on
HackSim. It is one Server Component with a single client island for the
prompt input. The textarea grows, the primary submit button sits next to a
secondary outline pill ("See an example run") and a small inline Settings
popover that controls builder, judge, and designer counts plus the small-mode
preset. Pressing Enter submits, Shift held adds a newline. Empty submits
surface an inline alert under the textarea so the failure is local rather
than a toast that vanishes.

The component contracts match `refs/UX_SPEC.md` section 4. Every visible
string is reviewed against `refs/PLAN.md` section 17.

## How to verify

```
cd apps/web
pnpm test components/HeroPrompt.test.tsx components/Nav.test.tsx components/Footer.test.tsx
pnpm dev
```

Open `http://localhost:3000`. Type a prompt, click "Spin up sim". Mock mode
routes to `/sim/sim_2026-04-28_a1b2c3`. Click "See an example run" to land
on the same sim. Open Settings, drag the builder slider, click "Small mode"
to verify the preset.

## Gensyn surface used

Indirect. `POST /api/sim` is the entry point that triggers the orchestrator
to spawn the AXL nodes for the sim. Real-mode requests proxy to FastAPI;
mock-mode requests return a fixed id without spawning anything.

## Up next

Commit 21 lands the live page. Five sections (Bounties, Builders,
Submissions, Judges, Verdicts), all driven by the snapshot fixture. The SSE
hook is plumbed in commit 22.
