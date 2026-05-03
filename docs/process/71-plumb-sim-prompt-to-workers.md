# 71. Plumb the user prompt to every role worker via HACKSIM_SIM_PROMPT

## What changed

The user's prompt at `POST /api/sim` (for example "a neighborhood app
for sharing local events and lost pets") never reached the bounty
designer, builder, or judge worker subprocesses. Each role's
`run(ctx)` started with `state.sim_prompt = ""`, the registered
`sim.prompt` envelope handler had no broadcaster on the other side,
and every Anthropic prompt template inside `decisions.py` and
`build.py` therefore saw an empty string. The user-visible symptom:
bounty descriptions rendered `"In the context of '', we want to see
a self-contained demo a curious peer can run and play with."` and
project titles looked generic and prompt-blind.

This commit plumbs the prompt end to end:

- `Spawner.__init__` accepts a new `sim_prompt: str = ""` keyword.
  When the prompt is non-empty, every spawned role worker process
  inherits it via the `HACKSIM_SIM_PROMPT` env var.
- `SimController` passes `sim_prompt=prompt` (the prompt the user
  POSTed) when constructing its `Spawner`.
- `packages/agents/worker.py` reads `HACKSIM_SIM_PROMPT` once and
  passes it to the role's `run()` as a keyword argument. A small
  `TypeError` fallback keeps the worker compatible with any role
  whose `run` does not yet accept `sim_prompt` (the four shipped
  roles all do after this commit).
- `bounty_designer.run`, `builder.run`, `judge.run`, and
  `organiser.run` all gain a `sim_prompt: str | None = None` keyword
  argument. Each stores it on `state.sim_prompt` so the existing
  Anthropic prompt builders in `decisions.py` and `build.py` see the
  real prompt instead of `""`.

## Why

Without the prompt, the deterministic stub fallback inside
`bounty_designer/decisions.py:144` rendered the literal `"In the
context of '', ..."` placeholder, and the Anthropic system prompt
inside `_propose_via_anthropic` had nothing to anchor to so the LLM
chose its sponsor archetype purely from the designer's peer id hash.
The reproduction was that a "neighborhood app" prompt produced a
"privacy primitives" bounty because the peer id happened to map to
Atlas Security regardless of what the user asked for.

The fix is the smallest end-to-end plumb: env var on subprocess
spawn, kwarg in `worker.py`, kwarg on every `run` signature.

After the fix, the same prompt produces:

- Drift sponsor: "Live Event Feed with Real-Time RSVP Presence"
- Lumen sponsor: "Event Feed Tracing and Performance Monitoring"
- Builder projects: "NeighborWatch - Observable Event & Pet Feed",
  "LocalWatch - Neighborhood Event & Pet Feed with OpenTelemetry"

All clearly tied to the user's "events and lost pets" framing.

## How to verify

- `pytest packages/agents/ packages/orchestrator/tests/test_controller.py packages/orchestrator/tests/test_spawner.py -q`
  reports 131 passed.
- Manual: `make demo`, type a custom prompt that names a specific
  domain (foods, sports, agriculture, anything). Confirm the
  bounty card descriptions and the project titles reference the
  prompt's nouns.

## Gensyn surface used

The prompt itself does not cross the AXL mesh; it lives on the
subprocess env vars only. The downstream Anthropic call inside each
worker is the surface that was broken; AXL transport is unchanged.

## Up next

RunLog autoscroll fix and the boot-state banner that shows "Spinning
up the AXL mesh" while builders register, both in the next commit.

## Files

`packages/orchestrator/spawner.py`,
`packages/orchestrator/controller.py`,
`packages/agents/worker.py`,
`packages/agents/bounty_designer/role.py`,
`packages/agents/builder/role.py`,
`packages/agents/judge/role.py`,
`packages/agents/organiser/role.py`,
`docs/process/71-plumb-sim-prompt-to-workers.md`.
