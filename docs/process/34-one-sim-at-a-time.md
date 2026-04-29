# 34. One sim at a time and tighter agent caps

## What changed

Two related problems showed up when a reviewer clicked Spin up sim twice without killing the previous run:

1. Each click created a new `SimController`, but old controllers stayed running with all their AXL nodes. Five sims left around 95 nodes on the loopback mesh; `bounty.posted` gossip drowned in the chatter and the new sim's snapshot accumulator never saw any bounties.
2. The `SettingsPopover` let users push counts to 20 builders, 9 designers, 5 judges (35 nodes for a single sim). The AXL recv queue is bounded at 100 messages per node, and 35 nodes with re-broadcast plus gossip on a fresh local mesh saturate the queue before bounties can propagate.

Fixes:

- `packages/orchestrator/api.py`: `POST /api/sim` now stops every prior controller before starting a new one. The orchestrator runs one simulation at a time. Stops happen in parallel as background tasks so the new sim's spawn does not wait for slow shutdowns. The hub channel for each prior sim is closed too so subscribers attached to the old stream finish cleanly.
- `packages/orchestrator/api.py`: `SimConfig` limits tightened to `builders 1..10` (was 1..32), `judges 1..5` (was 1..10), `designers 1..5` (was 1..10). A short comment in the model explains the reason so the next person who reads the file knows why the caps look small.
- `apps/web/components/HeroPrompt.tsx`: `SettingsPopover` sliders match the new caps and a small note under the sliders explains the loopback-mesh constraint so users do not feel arbitrarily limited.

15 orchestrator API tests pass. 65 vitest tests pass.

## Why

These are demo-friendly numbers. A real multi-host AXL deployment can go bigger; the loopback mesh on a single laptop cannot, and a demo that silently dies because the queue saturated is worse than a demo that refuses to overcommit.

The one-sim-at-a-time rule is also an honesty fix. The home page presents Spin up sim as a single primary action; behind the scenes letting it stack controllers without bound is a mismatch between what the UI implies and what the orchestrator does. Stopping the prior sim on each new POST makes the model match the UI.

Stopping in parallel matters because `controller.stop()` waits for AXL nodes to exit cleanly, which can take several seconds per node. Sequential stops would block the new sim's response for the time it takes to drain every prior sim. Background tasks let the HTTP response return immediately while old controllers wind down.

## How to verify

```
.venv/bin/pytest packages/orchestrator/tests/test_api.py -v
cd apps/web && bun run test
```

End-to-end:

```
make demo
```

Click Spin up sim, then click it again before the first run finishes. Confirm:

- The orchestrator log shows the prior controller stopping, with its AXL node teardowns.
- The new sim spawns within a couple of seconds; it does not wait for the prior teardowns.
- Only the new sim populates bounties; the old sim's stream is closed.

Open Settings and confirm the builders slider tops out at 10, judges at 5, designers at 5. The note below the sliders explains the cap.

## Gensyn surface used

Indirectly. The cap is set by the AXL recv queue size on each node and by the practical limit of how many AXL nodes the loopback Yggdrasil mesh can carry without dropping gossip. The `SimController.stop` path already exists; this commit just calls it from the API layer.

## Up next

The live page is correct now (commit 33) and stable under repeated clicks (this commit), but a viewer who has never seen the system still has to translate `phase: 1, builders: 8, bounties: 3` into "what is happening." The next commit adds a plain-English status banner above the stat pills.
