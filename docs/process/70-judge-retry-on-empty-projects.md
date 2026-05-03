# 70. Judges retry scoring while their project list is empty

## What changed

The judge phase tick handler in `packages/agents/judge/role.py` used
to bail with a `judge.no_projects` event the first time it ran with
an empty `state.projects` dict. The intent was to short-circuit the
scoring loop when no projects exist; in practice it dropped every
late-arriving submission on the floor because the JUDGING phase tick
beats `project.submitted` envelopes through the loopback mesh under
tight pace settings.

Trace from the readiness audit (sim_2026-05-03_3f343321,
`pace=smoke`):

```
t=52.68  phase.tick phase=3 (JUDGING)
t=52.84  judge.no_projects (BAIL)        <- handler returned here
t=53.79  project.submitted proj_8b27...   <- arrived after the bail
t=54.39  judge.heard_project proj_8b27...
t=59.04  project.submitted proj_8089...   <- 6 seconds late
```

Final state: phase 4, 3 projects, 0 verdicts. Demo blocker.

The fix splits `_on_phase_tick` into a thin entry that resets the
retry budget and a `_judge_round` worker that publishes the rubric
(once), scores any unscored projects, and reschedules itself if
either no projects were available yet or more might still arrive.
The retry budget is six rounds × five seconds, so the judge has
roughly thirty seconds of slack past the JUDGING tick to pick up
late submissions. The `state.scored` set keeps every round
idempotent.

After the fix (sim_2026-05-03_8489bba4, `pace=smoke`): 3 projects,
6 verdicts (was 0), 10 `judge.no_projects` events (the retries
firing as projects propagated). Phase 4 reached cleanly.

## Why this matters for the live demo

`pace=quick` already produced verdicts because the BUILD-to-JUDGING
gap is 45 seconds and Anthropic compose calls usually finish in 15
to 30. But a slow Anthropic call, a 429 rate limit retry, or any
small perturbation could push a single project.submitted past the
JUDGING tick under the old logic. The retry makes the judge robust
to any ordering hiccup in the loopback mesh, which is exactly the
class of bug `refs/DEMO_READINESS.md` flagged as the residual race
risk for live demo time.

## How to verify

- `pytest packages/agents/judge/ -q` reports 27 passed.
- Manual: `make demo`, type any prompt, click Spin up sim. Wait for
  phase 5. Verdicts cards show on the live page; the showcase
  ribbon ranks projects.
- Stress test: `curl -X POST http://127.0.0.1:8000/api/sim
  -H 'Content-Type: application/json' -d '{"prompt":"smoke","config":{"pace":"smoke"}}'`
  produces verdicts. Before this commit it produced zero.

## Gensyn surface used

Touches the run loop's per-judge state, not the AXL HTTP API. The
fix only schedules a deferred handler via the existing
`WorkerState.schedule` timer mechanism in `packages/agents/_runtime.py`.

## Up next

This closes the readiness checklist in `refs/DEMO_READINESS.md` §B2.
Remaining items in §C (envelope.unhandled noise,
duration_seconds null) are documented and out of scope for the live
demo.

## Files

`packages/agents/judge/role.py`,
`docs/process/70-judge-retry-on-empty-projects.md`.
