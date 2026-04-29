# 25. Snapshot accumulator

## What changed

New module `packages/orchestrator/snapshot.py` with `empty_snapshot`, `apply_event`, and `apply_events`. Pure functions: every call returns a new dict, the input is never mutated. Maps each HackSim envelope and one internal event (`builder.registered`) into the snapshot shape the frontend consumes.

Mapping:

- `phase.tick` advances `snapshot.phase`.
- `bounty.posted` appends to `bounties` (deduped by id).
- `team.formed` appends to `teams` (deduped by id) and updates each member's `team_id` and `current_bounty_id` on the builder row.
- `project.submitted` appends to `projects` with `status="submitted"` (deduped by project_id).
- `rubric.published` creates or updates a judge row.
- `verdict.published` appends to `verdicts` (deduped by judge per project), increments the judge's `scored_count`, flips the project's `status` to `judged`.
- `hackathon.closed` advances phase to SHOWCASE and stores the `leaderboard`.
- `builder.registered` (internal, emitted by SimController on spawn) seeds the builder roster with peer_id, display_name, skills.

Unknown events pass through without mutation; the SSE feed still sees them so the run log can show worker-internal noise like `designer.composing`.

19 tests cover empty initial state, every event-to-mutation rule, dedup behaviour for each, missing-field tolerance, and a purity test that asserts the input dict is unchanged after `apply_event`.

## Why

`POST /api/sim` (commit 28) starts a real simulation. The frontend's live page calls `GET /api/sim/{id}/snapshot` on mount and then subscribes to the SSE stream. The snapshot has to converge to "what is true right now" without the frontend replaying every event itself.

A pure accumulator makes the SimController's job tiny: every event that arrives gets folded through `apply_event`, the result is the new snapshot. The accumulator is unit-testable in isolation. Concurrency, threading, and the spawner stay out of these tests.

## How to verify

```
.venv/bin/python -m pytest packages/orchestrator/tests/test_snapshot.py -v
```

Expected: 19 passed in under 100ms.

## Gensyn surface used

None directly. The accumulator interprets the envelope payloads our protocol module (`packages/protocol/`) defines, but does not call AXL.

## Up next

Commit 26 lands the worker log tailer: a background task per role that reads JSON lines from the worker's stdout log and publishes them to the SseHub. Together with this accumulator, that gives us a live snapshot the FastAPI app can serve.
