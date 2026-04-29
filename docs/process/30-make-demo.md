# 30. `make demo`: orchestrator and frontend together

## What changed

- New `scripts/run_demo.sh`: pre-flight cleanup, ensures the AXL binary and the pnpm dependencies exist, starts the FastAPI orchestrator with `HACKSIM_AUTO_START=true` on port 8000, waits for `/api/health`, starts the Next.js dev server on port 3000 with `NEXT_PUBLIC_USE_MOCKS=false` and `ORCHESTRATOR_BASE_URL=http://127.0.0.1:8000`, waits for the hero, opens the browser, then loops on a periodic health probe. Trap-driven cleanup kills the dev server, the orchestrator, and any leftover AXL binaries on Ctrl-C.
- New `make demo` target invokes `scripts/run_demo.sh`. The previous `demo` target (which pointed at `scripts/run_sim.sh`, never written) was never functional.
- New `make smoke` target runs the headless `scripts/smoke_e2e.py` end-to-end harness for the backend.
- `make help` updated.

The frontend's `/api/sim/...` proxy routes (already in place from commits 20, 21, 22) hit `ORCHESTRATOR_BASE_URL` when `NEXT_PUBLIC_USE_MOCKS=false`, so the same UI that works against mock fixtures works against the live mesh with one env-var flip.

## Why

Until this commit, running the full stack required three terminals and several env vars set by hand. `make demo` is the contract: one command, hero opens in the browser, type a prompt, watch the simulation unfold. That is what reviewers will run.

The orchestrator-frontend integration was already in place at the route level (commit 28 added `auto_start`, the frontend has been proxying since commit 22). The runner ties them together with healthchecks and clean shutdown.

## How to verify

```
make demo
# wait ~10s for both processes to come up; the script opens the browser.
# Type a prompt, click Spin up sim, watch the live page.
# Ctrl-C to stop everything.
```

Alternative manual verification, no browser needed:

```
make demo &
sleep 10
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS -o /dev/null -w 'status=%{http_code}\n' http://127.0.0.1:3000/
ID=$(curl -s -X POST http://127.0.0.1:3000/api/sim \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"a research hackathon","config":{"pace":"smoke","builders":2,"judges":1,"designers":1}}' \
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["id"])')
sleep 75
curl -fsS http://127.0.0.1:3000/api/sim/$ID/snapshot \
  | python3 -m json.tool | head -20
```

The snapshot fetched through the frontend proxy reflects the real backend's live snapshot. Phase advances 0 -> 1 -> 2 -> 3 -> 4 over the configured pace.

## Gensyn surface used

No new endpoints. The runner glues processes together; the cross-mesh activity is the same sim the smoke harness has been driving since commit 22.

## Up next

The full stack is now testable end to end with one command. Optional follow-ups: configurability dials (tone, stakes, pace, format) on the SimConfig and persona templating; the README's "How this was built" section linking the per-commit process docs in order; a hosted Fly.io deploy.
