# 57. Audit P0 + P1 pass: must-fix and strong-polish landings

## What changed

The static audit captured in `refs/AUDIT_2026-04-30.md` enumerated
findings across three personas (layman user, ETHGlobal judge, Gensyn
mentor) plus dedicated frontend and backend passes. P0 marks
"must-fix before recording the video"; P1 marks "strong polish before
submission." Both tiers landed as separate commits, one per audit
bullet, in the order shipped:

- **P0-1.** Footer "Built on" link swaps "Claude Code" for "Anthropic
  Claude" so the wordmark and the FAQ no longer disagree about
  whether the running demo uses Claude Code.
- **P0-2.** Hero "See an example run" CTA targets `/examples` instead
  of a hardcoded sim id; the page itself spins up a real sim per tile
  (commit b4a0bcc shape).
- **P1-1.** RunLog header reads "replay" on the hosted Vercel preview
  by gating "live"/"offline" behind the same env-var check the
  HostedModeBanner uses.
- **P1-2.** HeroExamples accepts a `showHeader` prop; `/examples`
  page mounts headerless so the page heading and the embedded section
  no longer both render "Example runs".
- **P1-3.** SimConfig type gains a `pace` field, Settings popover
  grows a four-button radiogroup (Smoke / Quick / Medium / Deep), FAQ
  rewords "How long does a sim take" so the in-UI control is named.
- **P1-4.** SimController.start writes `HACKSIM_PACE` directly
  instead of via setdefault, so a second sim in the same orchestrator
  process picks up its own pace.
- **P1-5.** POST /api/sim awaits prior `controller.stop()` before
  spawning the new controller, so two rapid clicks no longer race
  shutdowns against the new spawn for ports.
- **P1-6.** New `SimErrorBanner` client component subscribes to the
  SSE stream on /sim/[id] and renders a coral alert when
  `sim.start_error` fires; previous notFound() path was the only
  signal a user got when SimController.start raised.
- **P1-7.** broadcast_now collects per-peer send failures across one
  fanout and emits one `axl.send_failed` event with a
  `failures: [...]` array, so a misconfigured mesh produces one log
  line per fanout instead of 14 peers x 2 retries = 28 lines per
  envelope.
- **P1-8.** ProjectDemoModal content-error and readme-error alerts
  speak in user terms (orchestrator may have stopped, check the
  terminal) rather than mentioning Next dev proxies.
- **P1-9.** Hero "Spin up sim" pending state shows a small CSS
  spinner plus the literal "Spinning up 15 AXL nodes..." label and an
  "about 10 seconds" hint.
- **P1-10.** Custom `apps/web/app/not-found.tsx` replaces the bare
  Next.js 404 with a Nav + Footer + three-CTA recovery page.
- **P1-11.** HostedModeBanner padding and hero pt trimmed so the home
  hero stays above the fold on a 1440x900 laptop with the banner
  present.
- **P1-12.** Section helper accepts an optional caption prop;
  Submissions section uses it to render "Click any tile to play the
  project the agents built" so a layman knows the tiles are
  interactive.
- **P1-13.** README "What is Gensyn AXL" paragraph splits into two:
  the AXL endpoint list lives on its own, the HackSim usage claim
  follows separately, with a forward link to the v2 MCP design.

## Why

P0 removes contradictions a panel could catch with ripgrep in under
five minutes (footer says Claude Code, FAQ says no; hero CTA points
at a 404). P1 is the thicker layer that turns the live page into
something a first-time visitor reads as polished rather than
debug-quality (loading affordance, real error banner, accessible
4-button pace selector, layout-mounted recorded-run notice on every
route). Together the two tiers land before the video shoot so the
recording captures the corrected shape on every surface.

## How to verify

```
.venv/bin/pytest packages/ tests/integration/ -q
cd apps/web && pnpm test
cd apps/web && pnpm exec tsc --noEmit
```

267 Python + 80 web tests pass; type check clean.

Manual: `make demo`, hit Spin up sim, watch the spinner. Click any
example tile; click into a project tile; switch tabs with `[` and
`]`. On the hosted preview the banner sits at the top of every page,
the live header carries `[ recorded YYYY-MM-DD ]`, and the run log
header reads "Run log . replay".

## Gensyn surface used

P1-7 changes the wire log shape on `/send` failures; existing AXL
HTTP behaviour is unchanged.

## Up next

P2 batch (commits 73-92): backend nits, broader docs, and tests for
the misconfigured-spawn path.
