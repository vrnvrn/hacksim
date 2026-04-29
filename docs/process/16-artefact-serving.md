# 16. Artefact serving with strict CSP

## What changed

- New module `packages/orchestrator/artefacts.py` defining `ArtefactStore`, `ArtefactRecord`, `ArtefactError`, and the `CSP_HEADER` constant.
- `ArtefactStore.register(sim_id, payload)` runs `git archive --format=tar | tar -x` against the builder's working tree at the named commit, materialising the tree under `sim-runs/{sim_id}/projects/{project_id}/`. Re-registration overwrites cleanly.
- `ArtefactStore.safe_path(sim_id, project_id, rel)` resolves a relative path inside the archive root, refusing absolute paths, traversal (`..`), and any out-of-bounds resolution.
- Three new FastAPI endpoints in `packages/orchestrator/api.py`:
  - `POST /api/sim/{sim_id}/projects`. Role workers POST the project.submitted payload here. The orchestrator archives, then publishes a `project.submitted` event into the SseHub for the frontend.
  - `GET /api/sim/{sim_id}/projects/{pid}/files`. JSON file listing for the Code tab.
  - `GET /api/sim/{sim_id}/projects/{pid}/static/{rel:path}`. Serves files with `Content-Security-Policy: default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; frame-ancestors 'self'`.
- Builder role POSTs to `HACKSIM_ORCH_URL/api/sim/{sim_id}/projects` after broadcasting on AXL. No-op when the env var is not set (smoke harness mode runs without an orchestrator).
- Spawner's `orch_url` constructor parameter populates `HACKSIM_ORCH_URL` for every role process.
- 15 new tests covering archive roundtrip, file metadata, re-registration, missing field error, missing working dir error, safe_path bounds, traversal rejection, register endpoint publishes to hub, files endpoint, files 404, static serves with CSP, static rejects traversal, register payload missing field returns 400.

## Why

Until this commit the agent built a real git-committed project, but no one could see it from outside the worker process. The orchestrator now serves the artefact at a stable URL the frontend iframe can load directly. The CSP stops the agent code from making network calls or escaping the iframe, which is the whole point of the static-frontend constraint we wrote into PLAN.md section 7.

The role-worker-to-orchestrator HTTP POST is the simplest pattern that keeps the AXL mesh as the agent-to-agent transport while letting the orchestrator catch up on submissions for the frontend. The wire still goes through Yggdrasil; the orchestrator HTTP call is local plumbing.

## How to verify

```
.venv/bin/python -m pytest packages/orchestrator/tests/test_artefacts.py -v
```

Expected: 15 tests pass. With a real builder write_project output, you can:

```
ID=$(curl -s -X POST http://127.0.0.1:8000/api/sim -H 'Content-Type: application/json' -d '{"prompt":"x"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
curl -X POST "http://127.0.0.1:8000/api/sim/$ID/projects" -H 'Content-Type: application/json' \
  -d "{\"project_id\":\"proj_x\",\"working_dir\":\"/tmp/hs_demo/project\",\"commit_hash\":\"$(cd /tmp/hs_demo/project && git rev-parse --short HEAD)\",\"entry_path\":\"index.html\"}"
open "http://127.0.0.1:8000/api/sim/$ID/projects/proj_x/static/index.html"
```

## Gensyn surface used

None new. The existing AxlClient.send already broadcasts the project.submitted envelope; this commit adds the orchestrator-side bookkeeping that complements it.

## Up next

Commit 17 lands the Judge role with a rubric and per-project scoring. Commit 18 lands the Organiser as the choreographer that emits phase ticks and tallies verdicts at the end.
