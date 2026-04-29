# 18. Organiser, choreography, re-broadcast and gossip

## What changed

This is the commit that closes the loop. After it, `make demo` produces a full lifecycle from prompt to leaderboard with every role participating.

Three concerns ship together because they only make sense as a whole:

### 1. Organiser role

New module `packages/agents/organiser/` with five files. CLAUDE.md, persona.py with `PACE_PRESETS` (smoke, quick, medium, deep), tally.py with `tally_leaderboard` (sort by avg verdict desc, ties break alphabetically), role.py with the run loop.

The organiser is the bootstrap. On startup it schedules four `phase.tick` broadcasts and the `hackathon.closed` tally at the configured pace (HACKSIM_PACE env var, defaults to `quick`). It accumulates `project.submitted` and `verdict.published` envelopes throughout. At `close_at` it computes the leaderboard and broadcasts `hackathon.closed` with the ranked projects.

### 2. Re-broadcast pattern

`WorkerState.fanout(wire, repeats=N, interval=S)` broadcasts now plus schedules N more re-broadcasts at `interval` seconds apart. Each re-broadcast re-reads `all_peer_ids()` so peers added to the topology between rounds catch up. All four roles use this for their primary envelope: bounty.posted, team.formed, project.submitted, verdict.published, rubric.published, plus the organiser's phase.tick.

### 3. Gossip

`WorkerState.register(envelope_type, handler, gossip=True)` flags an envelope type for re-fanout after the handler runs. The runtime calls `state.broadcast_now(msg.data)` on the original wire bytes. Dedupe by (sender_id, type, payload_id) ensures gossip terminates: a peer that has already seen a message neither dispatches nor re-gossips it.

The organiser is the universal relay: it sees every other role directly (it is the bootstrap), so registering `bounty.posted`, `team.formed`, `rubric.published`, `project.submitted`, `verdict.published` with gossip=True means every envelope that reaches the organiser is fanned out to the full mesh. Builders gossip `bounty.posted`. Judges gossip `bounty.posted` and `project.submitted`. The full schema makes propagation epidemic; one or two slow peers do not strand the rest.

### 4. Tests

New: 6 test files, 33 new tests. Total unit suite is 216 passed.

- `packages/agents/organiser/tests/test_tally.py`: 6 tests on the leaderboard.
- `packages/agents/organiser/tests/test_role.py`: 7 tests on accumulation, dedupe, phase emitter, close behaviour, idempotence.
- `packages/agents/_runtime.py`: existing 7 tests still pass with the new timer + gossip code paths.

### 5. Smoke harness

`scripts/smoke_e2e.py` rewritten for organiser-driven choreography. No more separate scribe injecting phase ticks. Spawn 1 organiser + 3 designers + 4 builders + 3 judges, wait for the configured pace's `close_at + 8s` grace, print per-role events and the final leaderboard. With `HACKSIM_PACE=smoke` (the new fastest preset, 75s end), this reliably produces 4 projects + 12 verdicts on a single machine.

## Why

Until this commit the smoke produced one project at most because Yggdrasil tree propagation on a fresh small mesh is slow: each role's `/topology` returns one or two peers initially, so a designer's broadcast only reaches a tiny subset, and re-broadcasts alone do not necessarily expand to fill the gap.

Three layers solve the problem at once:

- The organiser, which sees every peer because everyone connects to it, gossips every envelope it touches. That alone covers the cross-role hop where role-to-role topology is sparsest.
- Builder and judge gossip cover the hop where the organiser does not run a handler.
- Re-broadcast makes the original sender's first attempt cheap to retry as topology expands.

This is the same propagation pattern Gensyn's autoresearch demo relies on (re-share each finding once per cycle), generalised for our typed event vocabulary.

## How to verify

```
make build-axl
.venv/bin/python -m pytest -q --ignore=tests/integration   # 216 passed
.venv/bin/python -m pytest tests/integration/ -q           # 1 passed
.venv/bin/python scripts/smoke_e2e.py                      # full sim
```

Expected smoke output, abbreviated:

```
== HackSim smoke == run dir: /tmp/hacksim_smoke pace: smoke
spawned 11 roles total
running sim for 83s ...
== final leaderboard ==
  4 project(s), 12 verdict(s) tallied
  rank 1: Best Privacy Primitive Demo by cec43e
    score: 6.7  verdicts: 3
  rank 2: Best Use of an ML Model on Biological Data by a33022
    score: 6.67  verdicts: 3
  rank 3: Best Privacy Primitive Demo by 72a929
    score: 6.35  verdicts: 3
```

Each builder writes a real interactive index.html to its working directory; the script prints `open` paths.

## Gensyn surface used

`AxlClient.send` (broadcast and gossip), `AxlClient.recv` (handler dispatch), `AxlClient.get_topology` (fanout target enumeration). Same four-of-five HTTP endpoints exercised across the agent commits; MCP and A2A surfaces are still on the roadmap (configurability dial commit 25 plus future).

## Up next

`pnpm install` and verify the UX team's 98-file frontend tree in apps/web/. Then commit those in chunks 19 to 24. After that, the configurability dials (tone, stakes, pace, format) and the Playwright iframe smoke land in commit 25+.
