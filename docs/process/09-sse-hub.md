# 09. SSE multiplexer

## What changed

- New module `packages/orchestrator/sse.py` defining `Event` (one event with seq, type, data, sim_id, plus an SSE wire-format encoder) and `SseHub` (the many-to-many fan-out hub).
- `hub.publish(sim_id, event_type, data)` is sync, non-blocking, assigns a monotonic per-sim sequence id, appends to a per-sim ring buffer of configurable capacity (default 2000), and notifies every live subscriber via an asyncio queue.
- `hub.subscribe(sim_id, last_event_id=None)` is an async generator that first replays any buffered events with `seq > last_event_id`, then yields live events as they arrive. Cancellation removes the subscriber cleanly.
- `hub.close(sim_id)` marks a sim's channel closed and sends a None sentinel to every subscriber so their generators exit. Further publish calls raise.
- 16 unit tests cover sequence numbering, buffer capacity, per-sim isolation, close semantics, SSE wire format, replay below `last_event_id`, two-subscriber fan-out, sim filtering, close termination, capacity validation.

## Why

The browser UI subscribes to `/api/sim/:id/stream` once on mount. Behind that endpoint the orchestrator must:

1. Collect events from many sources (every role process publishes envelopes when it broadcasts or receives one, plus the orchestrator publishes phase ticks and lifecycle events).
2. Fan them out to many readers (the user's browser tab, plus possibly mirrors for debugging or the demo recording).
3. Survive reconnects via the standard SSE `Last-Event-ID` mechanism.

`SseHub` encapsulates all of that into one class with a sync `publish` and an async `subscribe`. The ring buffer means a reconnecting client gets up to 2000 missed events for free. The per-sim isolation means a busy sim never spams a quiet one's subscribers.

The `publish` method is sync because role processes call it from their handler threads and async-marshalling every event would be wasteful. Subscribers are async because they live inside FastAPI request handlers (commit 10) which are async.

## How to verify

```
.venv/bin/python -m pytest packages/orchestrator/tests/test_sse.py -v
```

Expected: 16 tests pass in roughly 130ms.

The SSE wire format conforms to the EventSource spec:

```
id: 42
event: bounty.posted
data: {"id":"b1","title":"FoldLab"}

```

(Each event terminates with a blank line.) The web UI's `useSse` hook (UX_SPEC.md section 8) consumes exactly this shape via the standard browser `EventSource`.

## Gensyn surface used

None. Pure orchestrator plumbing. The events that flow through the hub are the HackSim Envelopes from `packages/protocol/`, but the hub is transport-agnostic: it carries any JSON-serialisable dict tagged with a type.

## Up next

Commit 10 layers a FastAPI app on top of the spawner and the hub: `POST /api/sim` creates a simulation, `GET /api/sim/:id/snapshot` returns the current state, `GET /api/sim/:id/stream` is the SSE endpoint that calls into `hub.subscribe`. After commit 10 the backend has a complete API contract for the frontend to drive.
