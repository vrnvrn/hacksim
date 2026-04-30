# 58. Audit P2 pass: backend nits, broader docs, and verification tests

## What changed

P2 picks up where P1 left off. Each item is its own commit; the audit
plan in `refs/AUDIT_2026-04-30.md` lists them in the order shipped:

- **P2-1.** api.py inline comment naming the spawn population
  changes from "11 nodes" to the correct "15 nodes (1 organiser + 3
  designers + 8 builders + 3 judges)".
- **P2-2.** Settings popover preset button reads "Light mode (faster,
  fewer agents)" with the (3,1,1) figures in an aria-label; RunLog
  empty state reads "Booting the agents..." instead of the
  ambiguous "Waiting for the mesh to fill up...".
- **P2-3.** Tcpdump verification snippets in three places (RunItLocally,
  FAQ, ARCHITECTURE.md) get an inline note that macOS uses lo0 and
  Linux uses lo.
- **P2-4.** RunItLocally section gains `scroll-mt-24` so the
  `/docs#run-it-locally` deep link lands the panel below the sticky
  Nav and the hosted-preview banner.
- **P2-5.** New `docs/V2_MCP.md` extracts the MCP-based judging
  design from the gitignored refs/PLAN.md so a fork can pick the
  four-step path up.
- **P2-6.** New `tests/integration/test_axl_required.py` constructs
  a SimController with a missing axl_bin and asserts start() raises
  SpawnerError fast, proving the README claim that removing AXL
  silences the simulation.
- **P2-7.** New `packages/agents/tests/test_worker.py`; worker.py
  emits `worker.unknown_role` on stdout when HACKSIM_ROLE is not in
  the known set, and a separate `worker.import_error` on the
  ImportError branch.
- **P2-8.** ARCHITECTURE.md grows a "What changed from autoresearch"
  subsection with file-line citations on both sides; Gensyn
  mentor reading the FAQ comparison can now see the diff.
- **P2-9.** `_post_artefact_to_orchestrator` in builder/role.py
  carries an explicit "filesystem registration, not agent control"
  docstring naming which envelope types ride AXL.
- **P2-10.** `req.config.model_dump(exclude={"anthropic_api_key"})`
  drops the no-op exclude; the comment correctly names where the
  key safety actually lives (CreateSimRequest's `Field(exclude=True)`
  and SecretStr).
- **P2-11.** SimController.start emits `axl.binary` with the AXL Go
  binary's path / size / mtime so the run log shows which build is
  in play (AXL has no --version flag).
- **P2-12.** New `DELETE /api/sim/{id}` endpoint stops a running
  controller and clears the SSE channel; useful for a future "stop"
  UI button, plus two new tests.
- **P2-13.** Builder artefact registration retries once on transient
  failure with a 500ms backoff; surfaces a
  `builder.artefact_register_failed` event after two attempts so the
  run log shows why a project's modal eventually loads empty.
- **P2-14.** RunLog reads `window.matchMedia("(max-width: 1023px)")`
  on mount and starts collapsed on mobile; new chevron toggle in the
  header lets the user flip back, Pause control hides while
  collapsed.
- **P2-15.** `/sim/[id]` exports `generateMetadata` and sets a
  dynamic `<title>` from the snapshot prompt so a recovered tab
  reads "HackSim . "<prompt>"".
- **P2-16.** Live page header gains a small mono-cased "back to
  home" link above the prompt quote, matching the existing
  "[ now happening ]" tag style.
- **P2-17.** RunItLocally panel grows a "Watch a recorded run"
  subsection that mounts an asciinema-player slot pointed at
  `/tcpdump-demo.cast`; recording instructions live in
  `apps/web/public/tcpdump-demo.README.md`.

## Why

P2 hardens behaviour the rubric scores (depth of integration, code
quality, working examples) and resolves the smaller doc nits a
careful reader catches but a casual one misses. The
`tests/integration/test_axl_required.py` test in particular nails the
"removing AXL silences the simulation" claim with a fast assertion;
the worker.unknown_role event closes the silent-misconfig hole the
audit flagged.

## How to verify

```
.venv/bin/pytest packages/ tests/integration/ -q
cd apps/web && pnpm test
cd apps/web && pnpm exec tsc --noEmit
```

267 Python + 80 web tests pass; tsc clean.

Manual:
- `make demo`, observe the new `axl.binary` and (on artefact-post
  retry path) `builder.artefact_register_failed` events in the run
  log.
- `curl -X DELETE http://127.0.0.1:8000/api/sim/<id>` returns 204 and
  stops the sim.
- Resize the browser window to phone width while on `/sim/<id>`; the
  RunLog collapses with an Expand toggle.

## Gensyn surface used

P2-6 boots the Spawner with a missing AXL binary path and asserts
start fails; it does not call any AXL HTTP surface itself.
P2-11 emits a structured event but does not call AXL.

## Up next

P3 batch: cosmetic and edge polish across copy and small UX details.
