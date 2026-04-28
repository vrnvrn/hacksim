# 10. FastAPI orchestrator app

## What changed

- New module `packages/orchestrator/api.py`. `create_app(hub=None)` returns a FastAPI app with the three endpoints from `refs/UX_SPEC.md` section 6.
- `POST /api/sim`: validates the prompt and config (Pydantic models), allocates a sim id of the form `sim_YYYY-MM-DD_xxxxxx`, registers an in-memory record, publishes a `sim.created` event into the SseHub, returns the id and stream URL.
- `GET /api/sim/{sim_id}/snapshot`: returns the current `Snapshot` (id, prompt, config, phase, plus empty arrays for bounties, builders, teams, projects, judges, verdicts; those populate as commits 13+ land).
- `GET /api/sim/{sim_id}/stream`: returns a `text/event-stream` `StreamingResponse` whose generator subscribes to `hub.subscribe(sim_id, last_event_id=...)`. Honours the `Last-Event-ID` HTTP header for reconnect resume.
- `GET /api/health`: simple liveness with active sim count.
- CORS allows the dev frontend origin (`http://localhost:3000`).
- 12 tests in `packages/orchestrator/tests/test_api.py`. 11 of them run against `TestClient` directly. One end-to-end live test boots real uvicorn on a free port and verifies that two events (the `sim.created` from the POST plus a `phase.tick` published from outside) flow over the wire in order.

## Why

The orchestrator's external contract lands here. Everything the frontend talks to is now wired and tested. Subsequent commits (12, 22) layer behaviour onto these endpoints by populating snapshot fields and publishing more events into the hub; the API surface itself is fixed.

The `TestClient` proves request validation, status codes, error paths, CORS, and the hub-publish wiring. The live test proves the full SSE round-trip including server-sent flushing, which TestClient cannot reliably exercise because of how anyio buffers streaming responses. Together these two paths catch both shape regressions (TestClient) and wire-format regressions (uvicorn).

The `Snapshot` model returns empty arrays today. The Pydantic shape matches the TypeScript shape in `refs/UX_SPEC.md` section 7 byte for byte: the frontend can flip its mock fixture out for the real endpoint with no client-side change. That is the value of writing the spec first.

## How to verify

```
.venv/bin/python -m pytest packages/orchestrator/tests/test_api.py -v
```

Expected: 12 tests pass in roughly 2 seconds. The live SSE test takes about 1.5s by itself because it spins up uvicorn.

Smoke test the running app manually:

```
.venv/bin/uvicorn packages.orchestrator.api:app --host 127.0.0.1 --port 8000 &
curl -s -X POST http://127.0.0.1:8000/api/sim -H 'Content-Type: application/json' \
  -d '{"prompt":"a research hackathon"}' | jq .
curl -s http://127.0.0.1:8000/api/sim/<id>/snapshot | jq .
curl -N http://127.0.0.1:8000/api/sim/<id>/stream
```

The last command holds the connection open and prints SSE events as they arrive.

## Gensyn surface used

None. The hub carries Envelope-shaped events but the API itself is pure orchestrator. AXL endpoints come back into play in commit 12 when the spawned roles start publishing real envelopes into the hub.

## Up next

Commit 11 introduces the `hacksim-network` skill at `packages/skills/hacksim-network/`, mirroring `skills/autoresearch-network/` from the Gensyn demo. Slash commands wrap the local AXL HTTP API for use inside Claude Code role sessions. Commit 12 then layers Spawner support for booting a Claude Code session in a working directory with the skill installed, completing the agent harness.
