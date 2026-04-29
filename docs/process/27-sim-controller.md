# 27. SimController

## What changed

New module `packages/orchestrator/controller.py` with `SimConfig` and `SimController`.

A `SimController` owns one running simulation:

- a `Spawner` for the AXL nodes plus the role workers,
- one `LogTailer` per role process, attached with a listener that folds events through the snapshot accumulator,
- a live `snapshot` dict the FastAPI app serves on `GET /api/sim/{id}/snapshot`,
- async `start` and `stop` lifecycle hooks.

`start()` spawns the bootstrap organiser, then the configured designer / builder / judge population (default 3 / 8 / 3), wraps each in a tailer that listens to the worker stdout log, queries each builder's AXL node for its peer id, and publishes a `builder.registered` event so the live page renders builder chips immediately. Spawning happens in the executor pool so the calling FastAPI handler can return promptly.

`stop()` drains the tailers (so the snapshot reflects the workers' final emissions) then calls `Spawner.stop_all`, which terminates every worker and every AXL node in reverse order.

`_publish(event_type, payload)` is the SimController's own emitter for events that do not flow through a worker log (`builder.registered`, `sim.spawned`). It writes to the hub and folds into the snapshot in one step.

8 tests cover the start lifecycle (full population spawned), idempotent start, stop-stops-running, empty initial snapshot, internal event folds into snapshot, publish writes to both hub and snapshot, end-to-end tailer-to-snapshot through a real log file, and start seeds the builder roster on the snapshot via the topology query mock.

## Why

The pieces from commits 25 and 26 (accumulator, log tailer) plus the existing Spawner only become useful together. The SimController is the seam where they meet, and the place the FastAPI handler needs (commit 28). Keeping it small (about 150 lines of code) and exclusively orchestration logic means the moving parts stay individually testable.

## How to verify

```
.venv/bin/python -m pytest packages/orchestrator/tests/test_controller.py -v
```

Expected: 8 tests pass in roughly 1s. Tests use the Spawner's existing dependency-injection hooks (keygen, popen, wait_ready) so no real AXL binary is needed for the unit ring.

## Gensyn surface used

Indirectly: the SimController spins up real AXL nodes (via Spawner). It does not call AXL directly except through the `_query_peer_id` helper which hits `GET /topology` once per builder for the snapshot seeding step.

## Up next

Commit 28 wires `POST /api/sim` to start a SimController and exposes the live snapshot. Commit 29 adds the `make demo` target that boots the orchestrator and the frontend together.
