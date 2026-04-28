# 12. Role worker harness

## What changed

- New module `packages/agents/` with `worker.py` (CLI entrypoint), `_runtime.py` (shared event loop, signal handling, structured stdout emission), and a tests directory.
- `Spawner.spawn_role(role, index, is_bootstrap)` combines `Spawner.spawn(NodeSpec)` with launching a Python worker subprocess. The worker is started with three env vars: `AXL_API_PORT`, `HACKSIM_ROLE`, `HACKSIM_SIM_ID`, plus a `PYTHONPATH` that includes the repo root.
- `RoleHandle` dataclass groups a `NodeHandle` with its companion worker process; lifecycle methods stop the worker first (so it emits `worker.stopped` before the AXL node disappears) then the node.
- The worker dispatches by `HACKSIM_ROLE` to `bounty_designer.run`, `builder.run`, `judge.run`, or `organiser.run`. For roles whose modules have not landed yet (everything in this commit), the worker falls back to `_runtime.stub_heartbeat`, which drains envelopes and emits structured stdout events.
- `WorkerState.emit(event_type, payload)` writes a single JSON line to stdout. The orchestrator's log reader (commit 18) parses these lines and forwards them to the SSE hub. Until then the lines accumulate in `<work_dir>/<role>.<index>.worker.log` for inspection.
- `loop_until_closed` runs the dispatch loop with dedupe by (sender_id, type, payload_id) matching `research_network.py:320-374`. Handler exceptions are caught and emitted as `worker.handler_error` so one bad handler does not kill the worker.
- 7 new tests in `packages/agents/tests/test_runtime.py` (emit shape, handler dispatch, unhandled events, dedupe, exception isolation, non-envelope skipping, lifecycle events).
- 5 new tests in `packages/orchestrator/tests/test_spawner.py` for `spawn_role` (axl-then-worker order, env vars carried, distinct ports, role_handles property, stop_all ordering).

## Why

The agent harness now exists. Every commit from 13 onward writes a role module that exports `run(ctx)`; the spawner already knows how to bring it up. Without this commit the role personas would each have to invent their own process-spawning glue.

The fall-through to `stub_heartbeat` is deliberate. It means `make demo` can run today against fully stubbed roles and produce a real run log of envelopes flowing through the AXL mesh, even before any persona prompt is written. We keep "the demo runs" as a daily invariant.

The `JSON-line on stdout` emission style (one JSON object per line, written and flushed) is the same shape as the autoresearch demo's `run.log`. The orchestrator can `iter_lines` over the worker log file or attach to the worker's stdout pipe, and either way each event is a structured envelope.

Lite mode is the default. The worker imports `packages/skills/hacksim_network` and runs role logic in-process via the Anthropic SDK (commit 13+ wires the SDK call). Claude Code mode is a future stretch: same protocol, replace the worker entrypoint with one that launches a Claude Code session.

## How to verify

```
.venv/bin/python -m pytest packages/agents/tests/ packages/orchestrator/tests/test_spawner.py -v
```

Expected: 25 tests pass in roughly 6 seconds.

End-to-end smoke against a real binary (manual):

```python
from pathlib import Path
from packages.orchestrator import Spawner

with Spawner(
    base_dir=Path("/tmp/hacksim_smoke"),
    axl_bin=Path("third_party/axl/node"),
    sim_id="smoke",
) as s:
    org = s.spawn_role(role="organiser", is_bootstrap=True)
    b = s.spawn_role(role="builder", index=0)
    import time
    time.sleep(2)
    print((org.worker_log_path).read_text())
    print((b.worker_log_path).read_text())
```

Both worker logs should show `worker.started` lines, then any envelopes that flowed in (none yet, until commits 13+ make designers post bounties).

## Gensyn surface used

The full AXL surface from commit 11's skill module (`/topology`, `/send`, `/recv`) is used by the worker via `AxlClient`. No new endpoints.

## Up next

Commit 13 lands the BountyDesigner role. Persona-driven prompt to the Anthropic SDK, the designer composes one or more bounties and broadcasts `bounty.posted` envelopes. After that, builders (commit 14) listen for those bounties, builders submit (commit 15), the orchestrator serves the artefacts (commit 16), judges score (commit 17), and choreography drives the lifecycle (commit 18). At that point we have a full sim end to end.
