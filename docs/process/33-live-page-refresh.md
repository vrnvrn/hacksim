# 33. Live page now updates from snapshot refresh and SSE events

## What changed

Two distinct bugs were stopping the live page from reflecting the running sim. This commit fixes both.

1. The `useSse` hook treated the SSE `data:` line as the full envelope when it is in fact just the payload. The envelope type lives on the SSE `event:` line and arrives via `ev.type` when an `addEventListener` matches. Synthesis is now: type from `ev.type` (or `payload.type` for default messages), data from the parsed payload, ts from now, `from` sniffed off `sender_id` / `judge_peer_id` / `sponsor_peer_id` / `peer_id`. This is why the run log was rendering every line as `from anon -> {}`.
2. `apps/web/app/sim/[id]/page.tsx` is a Server Component that fetched the snapshot once and never updated. Adding a tiny `RefreshTicker` Client Component that calls `router.refresh()` every 2.5 s while `phase < 4` makes Next.js re-run the server fetch and reconcile the new HTML. Bounty cards, builder chips, projects, judges, and verdicts populate live without polling-and-state plumbing in the page.

`useSse` also now subscribes to every event type the orchestrator emits (plus worker-internal ones like `designer.composing`, `worker.started`) so the run log catches every transition.

Tests updated: `useSse` covers both the typed-event path and the default-message fallback. `RunLog` test feeds a typed event via the new `emitTyped` helper. 65 vitest tests pass; build clean.

## Why

A user on `make demo` clicked Spin up sim, watched the run log fill with `from anon -> {}` lines, and saw the snapshot stay frozen at zero bounties even though the orchestrator log showed bounties posting. Two distinct failure modes hidden behind one symptom.

Symptom one was a contract mismatch we wrote ourselves: the orchestrator publishes events as `event: bounty.posted\ndata: {...payload}` per the SSE spec, but the hook decoded `data` as the full envelope. The fix had to keep the default-message path working too because some events arrive without a typed `event:` line.

Symptom two was a Next.js App Router subtlety. A Server Component that reads from a server-side fetch will not re-fetch on its own, even when the client receives SSE events. We could have lifted the snapshot into a Client Component and managed state through a reducer, but a 25-line `RefreshTicker` is a much smaller surface and reuses the existing server fetch path; the SSE-driven run log already carries the realtime feel, the snapshot only needs to be eventually correct.

## How to verify

```
cd apps/web
bun run test                  # 65 vitest tests pass
bun run build                 # clean build
```

End-to-end:

```
make demo
```

Open `http://localhost:3000`, type a prompt, click Spin up sim. On the live page:

- The run log now shows lines like `[t+0.4s] sponsor_0 -> bounty.posted #b_0001 "Onchain micro-tippers"` instead of `from anon -> {}`.
- The four stat pills (agents, bounties, projects, verdicts) climb during the run.
- After about 75 seconds (smoke pace) the page reaches phase 4 and the View showcase link is reachable.

Open DevTools and watch the network panel: the SSE stream stays open, and a new server fetch fires every 2.5 s to `?_rsc=...` while phase < 4 (the App Router refresh).

## Gensyn surface used

None on this commit. The bug was entirely on the orchestrator-to-frontend boundary plus a Next.js-internal refresh pattern. The AXL nodes are unchanged.

## Up next

After fixing this, a second issue surfaced: a reviewer who clicks Spin up sim twice ends up with two SimControllers running, and 35 nodes saturate the loopback mesh queue. Tracked under commit 34, which adds a one-sim-at-a-time guard plus tighter agent caps in the SettingsPopover.
