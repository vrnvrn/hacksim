# 26. Worker log tailer

## What changed

New module `packages/orchestrator/log_tailer.py` with `LogTailer`. One async background task per role process. It opens the worker's stdout log file, reads new bytes as they appear, splits on newlines, parses each line as JSON, and publishes to the orchestrator's `SseHub`.

Optional `listener` callback (sync or async) fires for every parsed event so the SimController in commit 27 can fold events through the snapshot accumulator at the same time they go on the wire.

Robustness:

- Waits for the log file to appear before reading (worker creates it on startup; the tailer is started in parallel).
- Handles partial lines across reads (a JSON object split between two file reads is buffered until the newline arrives).
- Skips malformed JSON without crashing the loop.
- `stop(drain=True)` reads any final bytes before exiting so the snapshot reflects the worker's last words.

8 tests cover existing lines, lines appended after start, partial-line buffering, malformed JSON tolerance, sync listener, async listener (with `await`), waiting for file creation, and stop-drain behaviour.

## Why

Workers are subprocesses. Their stdout is captured to a log file by the spawner. Without this tailer, the FastAPI app never sees the events the workers emit, so the SSE stream stays empty and the frontend's run log shows nothing.

Async-not-threaded keeps the tailer in the FastAPI event loop. One tailer per role per sim is cheap; 11 tailers per running sim is a non-issue.

## How to verify

```
.venv/bin/python -m pytest packages/orchestrator/tests/test_log_tailer.py -v
```

Expected: 8 passed in roughly 3.5s. Tests use real temp-dir log files and the real `SseHub`, no mocks.

## Gensyn surface used

None directly. The tailer reads the structured stdout the workers emit (commit 12); those emissions are local to the worker process. The AXL surface is exercised by the workers themselves.

## Up next

Commit 27 lands `SimController`. It owns one running simulation: a `Spawner` for the AXL nodes plus the role workers, a `LogTailer` per role, the live snapshot, and lifecycle hooks. After commit 27, `POST /api/sim` (commit 28) creates a SimController and starts it, the FastAPI app exposes the live snapshot, and the frontend can talk to a real backend.
