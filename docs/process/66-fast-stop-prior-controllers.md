# 66. Fast-stop prior controllers before spawning a new sim

## What changed

`POST /api/sim` previously stopped every prior controller as a background
task (`asyncio.create_task(_stop_one(old))`) so the response returned in
under a second. The trade-off was that the prior sim's AXL Go binaries
kept running for up to 30 seconds while the spawner walked them through
the SIGTERM grace period one by one. During that window the new sim's
designers peered into the still-alive old mesh, broadcast `bounty.posted`
into it, and the new sim's own builders never heard a bounty. The
orchestrator snapshot stayed at zero bounties indefinitely.

The fix replaces the fire-and-forget background tasks with a single
`asyncio.gather` over a new fast-stop helper. Every prior controller's
`stop_fast` runs in parallel with a 2.5 second per-controller timeout.
Wall time of the response is now bounded by the slowest single stop,
typically well under three seconds, while every prior AXL process is
SIGKILLed before the new sim's spawner runs.

Three files changed:

- `packages/orchestrator/spawner.py`. New `Spawner.kill_all` method that
  sends SIGKILL to every worker and node Popen, reaps each with a 0.3s
  per-process wait, and closes the worker log fds so any attached
  tailers see EOF promptly.
- `packages/orchestrator/controller.py`. New `SimController.stop_fast`
  async method that detaches tailers without draining and dispatches
  `Spawner.kill_all` via the executor. Skips the recorder drain that
  `stop()` performs after tailers settle.
- `packages/orchestrator/api.py`. The block at lines 214 to 243 now
  awaits `asyncio.gather` of the per-controller fast-stops instead of
  scheduling them as background tasks.

## Why

Diagnostic trace for sim_2026-05-03_03f1803a: events.jsonl recorded
zero `bounty.posted` events but three `builder.heard_bounty` events.
The three new designer worker logs each contain a single line,
`worker.started`, and stop. The matching AXL logs show `Connected
outbound 200:448f:...@127.0.0.1:9100, Disconnected outbound`, after
which the AXL process logged nothing further. The bootstrap port at
9100 was held by an organiser from sim_2026-05-03_67827e2b that was
still in its SIGTERM grace period. Builders heard bounties from that
older mesh, designers in the new sim could not establish stable
peering, and the snapshot view at `/sim/<id>` stayed empty.

Awaiting the prior stops synchronously was the cheapest correct fix.
Using SIGKILL avoids the per-process wait that made the original
implementation choose background tasks in the first place.

## How to verify

- `pytest packages/orchestrator/tests/ -q` reports 125 passed.
- Manual: `make demo`, type a custom prompt, hit Spin up sim, watch
  the live page chips. Bounties show up within ~10 seconds of the
  redirect. Click Spin up sim again on a fresh prompt; the response
  arrives in under three seconds and the second sim also produces
  bounty cards.
- `lsof -i :9100` after the second spin-up shows exactly one AXL
  binary holding the bootstrap port (the new organiser), not the old
  one.

## Gensyn surface used

Indirect. The fix concerns the lifecycle of the AXL nodes that run
each role process. The mesh transport surfaces (topology, send, recv,
mcp) are unchanged; the bug was that stale processes kept the old
peer set alive on the loopback bootstrap port while the new processes
joined.

## Up next

Frontend timeout and status-aware error in HeroPrompt so a non-zero
HTTP status or a hung request surfaces a real message instead of the
generic "Could not reach the orchestrator" copy. See
`refs/UI_FIXES_PLAN.md` Fix 2.

## Files

`packages/orchestrator/spawner.py`,
`packages/orchestrator/controller.py`,
`packages/orchestrator/api.py`,
`refs/UI_FIXES_PLAN.md`,
`docs/process/66-fast-stop-prior-controllers.md`.
