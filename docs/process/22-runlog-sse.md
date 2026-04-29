# 22. RunLog component consumes SSE

## What changed

Added the SSE client at `apps/web/lib/use-sse.ts` and the `RunLog.tsx`
component. The hook owns one `EventSource` per page, parses each envelope,
and forwards it to a memoised callback. The component renders one terminal
line per envelope, auto-scrolls the pane unless the user has scrolled up by
more than a viewport and a half, and exposes a Pause toggle that freezes
auto-scroll without dropping events.

Mounted the run log on the right rail of `apps/web/app/sim/[id]/page.tsx`.
The mock stream route at `apps/web/app/api/mocks/stream/route.ts` replays
`apps/web/lib/mocks/stream.ndjson` at 1.5x real time, preserving the gaps
between events. The route caps inter-event gaps at four seconds so the demo
does not stall.

A screen-reader-only `aria-live="polite"` region announces only the latest
envelope, so users with assistive tech are not flooded.

## Why

The run log is the visible mesh. Every envelope a builder, judge, or
designer broadcasts arrives in this pane within 200ms. The pane is the
single piece of the live page that is genuinely streaming; everything else
is a snapshot patched by reducer logic the rest of the page wires up later.
Building the run log first lets us verify the hook against a real SSE
source before any reducer code lands.

The pause toggle exists because reviewers will want to read a specific
envelope mid-stream. Pause stops auto-scroll, the lines keep coming, the
view freezes.

## How to verify

```
cd apps/web
pnpm test components/RunLog.test.tsx
NEXT_PUBLIC_USE_MOCKS=true pnpm dev
```

Open `http://localhost:3000/sim/sim_2026-04-28_a1b2c3`. The run log on the
right pane fills line by line over about 90 seconds. Click "Pause" to freeze
the view. Click "Resume" to continue.

## Gensyn surface used

The hook consumes the SSE endpoint described in `refs/UX_SPEC.md` section 6.
The orchestrator builds that endpoint by polling `GET /recv` from each
agent's AXL node, the pattern lifted from `research_network.py` (see
`packages/orchestrator/sse.py` once commit 09 lands).

## Up next

Commit 23 lands `ProjectDemoModal.tsx`, the centerpiece. Three tabs (Demo,
Code, Verdict), iframe sandboxed with `allow-scripts` only.
