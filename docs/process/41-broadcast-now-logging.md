# 41. Surface per-peer send failures on the worker stdout channel

## What changed

`WorkerState.broadcast_now` used to swallow every send exception with a
bare `except Exception: pass`. When the AXL mesh was misconfigured
(bootstrap unreachable, peer port collision, key file unreadable) the
UI showed quiet starvation: bounties posted but never arrived,
verdicts vanished, the run log stayed silent. There was no signal in
the orchestrator log either.

Each failed send now emits an `axl.send_failed` event over the same
JSON-line stdout channel the runtime already uses for every other
worker event. The payload carries the destination peer id, the
exception class, and the message. The orchestrator's log tailer
forwards the event into SSE, the run log surfaces it, and the
underlying cause is visible without strace.

Files changed:

- `packages/agents/_runtime.py`: replaces the swallow with a structured
  `emit("axl.send_failed", ...)` call. Existing behaviour preserved:
  one peer failing does not stop the loop, the success counter only
  increments on `200 OK`, and `fanout` retries continue on schedule.
- `packages/agents/tests/test_runtime.py`: new
  `TestBroadcastNow.test_send_failure_is_emitted_as_event` asserts
  every per-peer failure produces one event with the expected fields.

## Why

A demo that quietly starves is the worst failure mode for a judge:
they see a hung UI, no error, and assume the whole stack is broken
when one config line is off. Surfacing the failure where the run log
already lives means a misconfigured node tells the operator what is
wrong in seconds, not minutes. Quality-of-code remediation flagged in
the second-pass judge review.

## How to verify

```
.venv/bin/pytest packages/agents/tests/test_runtime.py -q
.venv/bin/pytest packages/ -q
```

Eight runtime tests pass, 260 total tests pass.

Manual: kill the bootstrap AXL node mid-sim. Within one fanout cycle
the run log shows `axl.send_failed` events for every destination peer,
each with the underlying error message.

## Gensyn surface used

`POST /send`. The behaviour change is on our side; the AXL HTTP
contract is unchanged. The test exercises the failure path of
`AxlClient.send` (which raises `AxlError` on non-200) and the runtime
loop that wraps it.

## Up next

Promote the `axl.send_failed` event into the live page's status
banner if it fires more than N times in M seconds, so the UI tells a
judge "the mesh is starving" instead of just listing the events in the
run log.
