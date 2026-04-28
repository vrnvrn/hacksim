# 14. Builder role, listens and forms a team

## What changed

Same five-file shape as the BountyDesigner. `packages/agents/builder/` ships `__init__.py`, `CLAUDE.md`, `persona.py` (skill profile derivation, display name, persona text loader), `decisions.py` (`score_bounty_fit` and `pick_bounty` with stub heuristic + Anthropic SDK upgrade), `role.py` (run loop with `bounty.posted` accumulator and `phase.tick` -> TEAM_FORMATION trigger), plus `tests/test_decisions.py` (11 tests) and `tests/test_role.py` (7 tests).

Builder lifecycle in this commit:

- BOUNTY_DESIGN: every `bounty.posted` envelope received gets stored in an in-memory inbox keyed by bounty id. Duplicates are dropped, malformed envelopes (missing id) are skipped, and a `builder.heard_bounty` event lights up the run log.
- TEAM_FORMATION: when `phase.tick` arrives with phase=1, the builder picks the highest-scoring bounty and broadcasts `team.formed` with itself as the only member. Solo only for now; multi-builder team formation is a stretch.
- BUILD, JUDGING, SHOWCASE: not yet handled here. Lands in commits 15+.

## Why

This is the second concrete role and it follows the BountyDesigner template. The pattern is now clear: a role module exposes `run(ctx)`, defers the persona to a CLAUDE.md file, defers the decision to a stub-with-Anthropic-upgrade module, and registers handlers on the shared runtime loop. Future roles (judge, organiser) follow the same shape.

Solo team formation is intentional. Multi-builder teams require a back-and-forth handshake (`team.invite`, `team.accept`) and a tie-break when multiple builders want the same bounty. That logic is defensible to land in a follow-up commit, but not on the critical path to a working demo. The wire protocol leaves room: the `team.formed` envelope already carries `members` as a list, so the schema is forward-compatible.

The skill scoring heuristic is intentionally simple. It counts case-insensitive skill mentions in the bounty's title, description, qualification, and sponsor name. Tied scores break alphabetically by title, so picks are reproducible across runs. With ANTHROPIC_API_KEY set, the upgrade asks Claude to pick by id. Either way, picks are sane and explainable.

The skill pool covers languages, domains, and stacks (22 items). Profile size is fixed at 3 distinct skills per builder, picked deterministically from the peer id. For 8 builders, the chance of two builders sharing the same triple is vanishingly small.

## How to verify

```
.venv/bin/python -m pytest packages/agents/builder/tests/ -v
```

Expected: 18 tests pass in roughly 4 seconds.

## Gensyn surface used

`AxlClient.get_topology` and `AxlClient.send` for the broadcast. Same fan-out pattern as the BountyDesigner. Drain happens in the shared runtime loop.

## Up next

Commit 15 lands the build phase: on `phase.tick` -> BUILD, the builder writes a static web project (`index.html` + optional `style.css` + `app.js`) into its working directory, git commits, and broadcasts `project.submitted` with the commit hash and entry path. Commit 16 wires the orchestrator's `artefacts` module to git-archive the working tree and serve it under a strict CSP.
