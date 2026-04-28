# 15. Builder writes a static web project and submits

## What changed

- New module `packages/agents/builder/build.py` with `write_project(work_dir, bounty, skills, sender_peer_id, sim_prompt)`. Composes a single-page web project (`index.html` + `style.css` + `app.js`), writes the files into `work_dir`, runs `git init` if needed, stages everything, commits, and returns a metadata dict with the short commit hash, entry path, file list, title, and tagline.
- Stub composition produces a clean interactive page: header with sponsor / bounty title / skill pills, a description card with the qualification list, and a force-graph canvas where you click to add nodes and drag to move them. The accent hue is derived from the builder's peer id so two builders working on the same bounty produce visibly distinct demos.
- Anthropic upgrade asks Claude haiku 4.5 to compose the same shape, returning JSON with `title`, `tagline`, and `files`. Falls back to the stub on any SDK or parse failure.
- `role.py`'s `_on_phase_tick` now branches: TEAM_FORMATION calls `_form_team` (commit 14 behaviour), BUILD calls the new `_build_and_submit`, which calls `write_project` and broadcasts `project.submitted` with the commit hash, entry path, working dir, and file metadata. Submits exactly once per phase.
- `HACKSIM_BUILDER_WORK_DIR` env var lets the spawner point each builder at its dedicated working tree. Default is the cwd's `project/` subdirectory.
- 9 new tests in `packages/agents/builder/tests/test_build.py` cover required files in the composed project, HTML referencing companion files, sponsor and bounty title appearing in HTML, skills appearing as pills, no external network calls, two peers producing different style.css, files written to disk, git commit produces a hash, and file metadata sizes.

## Why

Without this commit, the builder picks a bounty but produces nothing visible. With this commit, every builder produces a real, runnable, sandboxable web project committed in its own git repo. The orchestrator (commit 16) `git archive`s those trees and serves them under a strict CSP; the showcase modal in the frontend renders them in iframes; reviewers click winners and play the agents' actual output.

The stub is intentionally interactive (clickable, draggable canvas) rather than static text. A reviewer who runs `make demo` without an Anthropic key still sees something they can play with. With a key, the same template gets richer per-bounty content via Claude. Either way the wire format is identical.

The accent hue derivation from peer id is the simplest visual variation that makes "two builders, two projects" obvious to a layman scrolling the showcase. It costs nothing.

The forbidden-tokens test in `test_html_no_external_network_calls` is a guardrail. The static frontend constraint is core to the sandboxing story (see PLAN.md section 7); a builder that injects a CDN URL would break iframe playback. The test catches it at unit time.

## How to verify

```
.venv/bin/python -m pytest packages/agents/builder/tests/ -v
```

Expected: 27 tests pass in roughly 4 seconds. Tests skip cleanly if `git` is not on PATH.

End-to-end smoke (manual, requires AXL binary):

```python
from pathlib import Path
from packages.agents.builder.build import write_project

result = write_project(
    work_dir=Path("/tmp/builder_smoke/project"),
    bounty={
        "id": "bnt_x",
        "title": "Best Visualisation Tool",
        "sponsor_name": "FoldLab",
        "description": "Build a viz a layman can use.",
        "qualification": ["uses real data", "works in iframe"],
    },
    skills=["Python", "viz", "ML"],
    sender_peer_id="a" * 64,
    sim_prompt="research hackathon",
)
print(result)
# Then: open /tmp/builder_smoke/project/index.html in a browser.
```

## Gensyn surface used

`AxlClient.send` for the `project.submitted` broadcast, same fan-out pattern as previous roles. No new AXL endpoints. The `git` operations are local; nothing crosses the mesh except the commit hash.

## Up next

Commit 16 lands `packages/orchestrator/artefacts.py`. On `project.submitted`, the orchestrator copies the working tree (at the named commit) into `sim-runs/{sim_id}/projects/{project_id}/`, registers it on a static-file route, and adds it to the snapshot's projects list. The route serves with a strict Content-Security-Policy header so the iframe sandbox holds.
