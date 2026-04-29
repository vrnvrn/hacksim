# 28. POST /api/sim spawns a real simulation

## What changed

Wires `POST /api/sim` to start a real `SimController` when the app is constructed with `auto_start=True` (the default in production via `HACKSIM_AUTO_START=true`). The endpoint returns the new sim id and starts the spawn process in the background. `GET /api/sim/{id}/snapshot` returns the controller's live snapshot.

`create_app` gains four new keyword args: `auto_start`, `base_dir`, `axl_bin`, `orch_url`. Each defaults from an env var (`HACKSIM_AUTO_START`, `HACKSIM_RUNS_DIR`, `HACKSIM_AXL_BIN`, `HACKSIM_ORCH_URL`). Tests pass `auto_start=False` to keep the unit ring fast.

The `SimConfig` Pydantic model gains a `pace` field (default `quick`; values `smoke`, `quick`, `medium`, `deep`). The `pace` flows through into `ControllerConfig`, which the SimController forwards to the organiser's choreography schedule.

The shutdown hook (`@app.on_event("shutdown")`) iterates `app.state.controllers` and stops each so workers and AXL nodes do not leak when the server restarts.

`/api/health` now reports the `auto_start` flag and counts both legacy records and live controllers as `active_sims`.

3 new tests cover: POST with auto_start creates a controller, GET snapshot returns the controller's live snapshot, and the health endpoint reports the flag. The existing 12 tests still pass under `auto_start=False`.

## Why

This commit is what flips the orchestrator from "demo plumbing" into the real backend the frontend talks to. After this, `cd apps/web && pnpm dev` plus the orchestrator running in another terminal produces a live sim from a single browser POST.

The background-start pattern means the HTTP response is fast (sim id returned in well under 100ms) while AXL nodes come up over the next ten or so seconds. The frontend can subscribe to the SSE stream immediately and watch the population join.

Pace makes its way into the contract here so the configurability dials we sketched (commit 30+) have a place to land without another wire change.

## How to verify

```
.venv/bin/python -m pytest packages/orchestrator/tests/test_api.py -v
```

Expected: 15 passed. End-to-end smoke against a running orchestrator (commit 29):

```
make build-axl
HACKSIM_AUTO_START=true HACKSIM_AXL_BIN=$(pwd)/third_party/axl/node \
  .venv/bin/uvicorn packages.orchestrator.api:app --port 8000 &
curl -s -X POST http://127.0.0.1:8000/api/sim \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"a research hackathon","config":{"pace":"smoke","builders":3,"judges":2,"designers":2}}'
sleep 30
curl -s http://127.0.0.1:8000/api/sim/<id>/snapshot | python3 -m json.tool
```

The snapshot returns a sim with phases progressing, builders registered, bounties posted (timing depends on the chosen pace).

## Gensyn surface used

Indirectly: every cross-agent byte still goes through the AXL mesh that SimController spawns. The HTTP API is purely the front door and the snapshot view. No new AXL endpoints are introduced.

## Up next

Commit 29 lands the `make demo` target and the `apps/web/.env.local` flip so the frontend talks to the live orchestrator. After that, a single `make demo` boots the full stack.
